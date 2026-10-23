"""Per-file target assignment exports and source provenance."""
import fnmatch
import hashlib
import json
import struct
import xml.etree.ElementTree as ET
from .sorting import natural_key
from .saved_peaks import read_saved_peaks
from .csv_io import write_csv
from .targets import MATCH_FIELDS, PEAK_FIELDS
from .target_matching import discover_peaks, match_targets

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
