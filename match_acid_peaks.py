"""Discover late peaks or match user-defined acid targets to saved LCD peaks.

Examples:
  python match_acid_peaks.py FOLDER --output results
  python match_acid_peaks.py FOLDER --targets targets.csv --output results
  python match_acid_peaks.py --write-example-targets targets.csv

No chemical identity is inferred from peak size. Matching needs retention times
from standards under the same method. Multiple candidates and overlapping target
assignments are flagged and left without a reported area.
"""
import argparse
import csv
import fnmatch
import hashlib
import json
import math
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

from batch_extract_areas import natural_key, read_saved_peaks, write_csv
from plot_hplc import DEFAULT_SOURCE


TARGET_FIELDS = ["target_name", "detector", "expected_rt_min", "tolerance_min", "min_area_uV_s"]
DETECTORS = {"RI", "UV_210nm", "UV_254nm"}
MATCH_FIELDS = ["filename", "target_name", "detector", "expected_rt_min", "tolerance_min",
                "min_area_uV_s", "min_retention_time_min", "status", "candidate_count",
                "peak_number", "retention_time_min", "rt_error_min", "area_uV_s", "height_uV",
                "start_min", "end_min", "note"]
PEAK_FIELDS = ["filename", "detector", "peak_number", "retention_time_min", "area_uV_s",
               "height_uV", "start_min", "end_min", "relative_area_percent", "passes_discovery_filter"]


def finite_number(value, name, minimum=0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a finite number.") from None
    if not math.isfinite(number) or number < minimum:
        raise ValueError(f"{name} must be finite and >= {minimum}.")
    return number


def load_targets(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not set(TARGET_FIELDS).issubset(reader.fieldnames):
            raise ValueError("Target CSV requires: " + ", ".join(TARGET_FIELDS))
        targets = []
        seen = set()
        for line, row in enumerate(reader, 2):
            target = {key: row[key].strip() if row[key] is not None else "" for key in TARGET_FIELDS}
            if not target["target_name"] or target["detector"] not in DETECTORS:
                raise ValueError(f"Target CSV line {line}: name required; detector must be RI, UV_210nm, or UV_254nm.")
            identity = target["target_name"], target["detector"]
            if identity in seen:
                raise ValueError(f"Duplicate target/detector on line {line}: {identity}")
            seen.add(identity)
            for key in TARGET_FIELDS[2:]:
                target[key] = finite_number(target[key], key)
            if target["tolerance_min"] == 0:
                raise ValueError("Retention tolerance must be > 0.")
            targets.append(target)
    if not targets:
        raise ValueError("Target CSV has no targets.")
    return targets


def match_targets(channels, targets, min_retention_time=5.0):
    """Match exactly one qualifying peak per target; reject ambiguity/reuse.

    The per-target absolute area cutoff is independent of other acids' sizes.
    Global relative-area filtering is used only for discovery, never matching.
    """
    floor = finite_number(min_retention_time, "Minimum retention time")
    by_detector = {channel["key"]: channel for channel in channels}
    matches = []
    candidates_export = []
    assignments = {}
    for target in targets:
        row = {field: "" for field in MATCH_FIELDS if field != "filename"}
        row.update(target)
        row["min_retention_time_min"] = floor
        row["candidate_count"] = 0
        center, tolerance = target["expected_rt_min"], target["tolerance_min"]
        if center < floor:
            row["status"] = "target_below_retention_cutoff"
        elif target["detector"] not in by_detector:
            row["status"] = "missing_detector"
        else:
            channel = by_detector[target["detector"]]
            in_window = [p for p in channel["peaks"] if p["retention_time_min"] >= floor
                         and abs(p["retention_time_min"] - center) <= tolerance + 1e-12]
            eligible = [p for p in in_window if p["area_uV_s"] > 0 and p["area_uV_s"] >= target["min_area_uV_s"]]
            row["candidate_count"] = len(eligible)
            for peak in in_window:
                candidates_export.append({"target_name": target["target_name"], "detector": target["detector"],
                                          **peak, "passes_min_area": peak in eligible})
            for peak in eligible:
                assignments.setdefault((target["detector"], peak["peak_number"]), []).append(len(matches))
            if not eligible:
                row["status"] = "below_min_area" if in_window else channel.get("status", "not_detected")
                if row["status"] == "ok":
                    row["status"] = "not_detected"
            elif len(eligible) > 1:
                row["status"] = "ambiguous_multiple_peaks"
            else:
                peak = eligible[0]
                row.update(peak)
                row["rt_error_min"] = peak["retention_time_min"] - center
                row["status"] = "matched"
        matches.append(row)
    for indexes in assignments.values():
        if len(indexes) > 1:
            for index in indexes:
                row = matches[index]
                if row["status"] == "matched":
                    row["status"] = "assignment_conflict"
                row["note"] = "Same saved peak is a candidate for multiple targets; review target windows."
                for key in ["peak_number", "retention_time_min", "rt_error_min", "area_uV_s", "height_uV", "start_min", "end_min"]:
                    row[key] = ""
    return matches, candidates_export


def discover_peaks(channels, min_retention_time=5.0, min_area=1000.0, relative_percent=1.0):
    floor = finite_number(min_retention_time, "Minimum retention time")
    minimum = finite_number(min_area, "Minimum area")
    relative = finite_number(relative_percent, "Relative area percent")
    if relative > 100:
        raise ValueError("Relative area percent must be <=100.")
    rows = []
    for channel in channels:
        late = [p for p in channel["peaks"] if p["retention_time_min"] >= floor and p["area_uV_s"] > 0]
        reference = max((p["area_uV_s"] for p in late), default=0)
        threshold = max(minimum, reference * relative / 100)
        for peak in late:
            rows.append({"detector": channel["key"], **peak,
                         "relative_area_percent": peak["area_uV_s"] / reference * 100,
                         "passes_discovery_filter": peak["area_uV_s"] >= threshold})
    return rows


def export_folder(folder, output, targets=None, min_retention_time=5.0, min_area=1000.0,
                  relative_percent=1.0, include="*.lcd", excludes=()):
    discover_peaks([], min_retention_time, min_area, relative_percent)
    files = sorted((p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".lcd"
                    and fnmatch.fnmatchcase(p.name.lower(), include.lower())
                    and not any(fnmatch.fnmatchcase(p.name.lower(), x.lower()) for x in excludes)),
                   key=lambda p: natural_key(p.name))
    if not files:
        raise ValueError("No matching LCD files.")
    matches, candidates, discovered, report = [], [], [], []
    for source in files:
        info = {"filename": source.name, "status": "ok", "error": ""}
        try:
            info["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
            channels = read_saved_peaks(source)
            info["saved_peak_count"] = sum(len(c["peaks"]) for c in channels)
            discovered.extend({"filename": source.name, **row} for row in discover_peaks(channels, min_retention_time, min_area, relative_percent))
            if targets is not None:
                rows, options = match_targets(channels, targets, min_retention_time)
                matches.extend({"filename": source.name, **row} for row in rows)
                candidates.extend({"filename": source.name, **row} for row in options)
        except (OSError, ValueError, AssertionError, struct.error, ET.ParseError) as error:
            info["status"], info["error"] = "file_error", f"{type(error).__name__}: {error}"
            for target in targets or []:
                row = {key: "" for key in MATCH_FIELDS}
                row.update(target, filename=source.name, status="file_error", note=info["error"])
                matches.append(row)
        report.append(info)
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "discovered_peaks.csv", discovered, PEAK_FIELDS)
    write_csv(output / "large_peaks_after_cutoff.csv", [r for r in discovered if r["passes_discovery_filter"]], PEAK_FIELDS)
    if targets is not None:
        write_csv(output / "target_matches.csv", matches, MATCH_FIELDS)
        fields = ["filename", "target_name", "detector", "peak_number", "retention_time_min", "area_uV_s", "height_uV", "start_min", "end_min", "passes_min_area"]
        write_csv(output / "target_candidates.csv", candidates, fields)
    metadata = {"source_folder": str(folder.resolve()), "include": include, "exclude": list(excludes),
                "min_retention_time_min": min_retention_time, "discovery_min_area_uV_s": min_area,
                "discovery_relative_area_percent": relative_percent, "targets": targets,
                "target_matching": "Exactly one positive saved peak above the per-target absolute minimum within expected RT +/- tolerance. Ambiguous/shared matches have blank areas. Relative-area filter applies only to discovery.",
                "identity_note": "RT matching is a candidate assignment, not confirmation of chemical identity. Example target labels are not acid identifications.",
                "files": report}
    (output / "matching_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    errors = sum(r["status"] != "ok" for r in report)
    print(f"Processed {len(files)} files; {errors} errors; {len(discovered)} positive saved peaks after {min_retention_time:g} min.")
    if targets is not None:
        from collections import Counter
        print("Target statuses:", dict(Counter(r["status"] for r in matches)))
    print("Output:", output.resolve())
    return matches, discovered, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", nargs="?", type=Path, default=DEFAULT_SOURCE.parent)
    parser.add_argument("--targets", type=Path, help="CSV with per-acid, per-detector expected RTs and tolerances")
    parser.add_argument("--write-example-targets", type=Path, help="Write a provisional unlabeled 47A0 example CSV, then exit")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "batch_results" / "target_matching")
    parser.add_argument("--min-retention-time", type=float, default=5)
    parser.add_argument("--min-area", type=float, default=1000, help="Discovery only; target minima come from target CSV")
    parser.add_argument("--min-relative-area-percent", type=float, default=1, help="Discovery only; does not reject weaker acid targets")
    parser.add_argument("--include", default="*.lcd")
    parser.add_argument("--exclude", action="append", default=[], help="Filename/glob to skip; repeat for multiple patterns")
    args = parser.parse_args()
    try:
        if args.write_example_targets:
            if args.write_example_targets.exists():
                raise ValueError("Example target file already exists; choose another path to preserve your edits.")
            rows = [{"target_name": "unidentified_47A0_peak", "detector": key,
                     "expected_rt_min": rt, "tolerance_min": 0.15, "min_area_uV_s": 1000}
                    for key, rt in [("RI", 7.1463), ("UV_210nm", 6.8845), ("UV_254nm", 6.8830)]]
            write_csv(args.write_example_targets, rows, TARGET_FIELDS)
            print("Wrote provisional example (replace labels/times with standards):", args.write_example_targets)
            return
        targets = load_targets(args.targets) if args.targets else None
        _, _, metadata = export_folder(args.folder, args.output, targets, args.min_retention_time,
                                       args.min_area, args.min_relative_area_percent, args.include, args.exclude)
        if any(r["status"] != "ok" for r in metadata["files"]):
            raise SystemExit(1)
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
