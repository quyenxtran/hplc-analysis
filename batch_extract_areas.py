"""Export saved Shimadzu peak areas from a folder of LCD files.

Reads the vendor's PT-* peak tables; does not reintegrate raw chromatograms.
Writes every saved peak, a filtered large-peak table, and a main-peak summary.
Default filter: apex in 6-12 min, area >=1000 uV*s, and >=1% of the largest
positive peak per file/detector within that window. Thresholds are adjustable.
Layout reference:
https://github.com/ethanbass/chromConverter/blob/master/R/read_shimadzu_peaktable.R
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import struct

import olefile

from plot_hplc import DEFAULT_SOURCE, read_xml


def natural_key(value):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", str(value))]


def parse_peak_table(raw):
    """Decode validated VER1 records, retaining vendor area/height precision."""
    if len(raw) < 20 or raw[:4] != b"VER1":
        raise ValueError("Expected a Shimadzu VER1 peak table with a 20-byte header.")
    count = struct.unpack_from("<I", raw, 4)[0]
    if count == 0:
        # These LCDs reserve one all-zero 792-byte record even for zero peaks.
        if any(raw[20:]):
            raise ValueError("Zero-peak table has unexpected nonzero payload.")
        return []
    record_length, remainder = divmod(len(raw) - 20, count)
    if remainder or record_length < 728:
        raise ValueError("Invalid VER1 peak record length.")
    peaks = []
    for index in range(count):
        offset = 20 + index * record_length
        retention_ms = struct.unpack_from("<I", raw, offset + 4)[0]
        area = struct.unpack_from("<d", raw, offset + 8)[0]
        height = struct.unpack_from("<d", raw, offset + 24)[0]
        start_ms, end_ms = struct.unpack_from("<2I", raw, offset + 56)
        if not math.isfinite(area) or not math.isfinite(height):
            raise ValueError("Peak area or height is not finite.")
        if not start_ms <= retention_ms <= end_ms:
            raise ValueError("Saved retention time lies outside saved peak bounds.")
        peaks.append({
            "peak_number": index + 1,
            "retention_time_min": retention_ms / 60000,
            "area_uV_s": area, "height_uV": height,
            "start_min": start_ms / 60000, "end_min": end_ms / 60000,
        })
    return peaks


def read_saved_peaks(path):
    channels = []
    with olefile.OleFileIO(path) as compound:
        metadata = read_xml(compound.openstream(["LSS Raw Data", "2D Data Item"]).read())
        status = compound.openstream(["LSS Raw Data", "Chromatogram Status"]).read()
        for node in metadata.findall("DII"):
            channel_id = node.findtext("DSID", "")
            if ".CH#" not in channel_id:
                continue
            channel_number = int(node.findtext("CN"))
            record = status[(channel_number - 1) * 64:channel_number * 64]
            display_unit = record[40:64].split(b"\x00")[0].decode("ascii")
            if display_unit != "mV":
                raise ValueError(f"Unsupported display unit {display_unit}; cannot label saved area as uV*s.")
            wavelength = node.findtext("ADN", "")
            if node.findtext("DSN", "").startswith("RID"):
                label, key = "Refractive index", "RI"
            elif wavelength in ("210nm", "254nm"):
                label, key = f"UV at {wavelength}", "UV_" + wavelength
            else:
                raise ValueError(f"Unexpected detector/wavelength: {channel_id} / {wavelength}")
            stream = ["LSS Data Processing", "PT-" + channel_id]
            if not compound.exists(stream):
                peaks, channel_status = [], "no_saved_peak_table"
            else:
                peaks = parse_peak_table(compound.openstream(stream).read())
                channel_status = "ok" if peaks else "no_saved_peaks"
            channels.append({"key": key, "detector": label, "channel_id": channel_id,
                             "stream": "/".join(stream), "status": channel_status, "peaks": peaks})
    if sorted(c["key"] for c in channels) != ["RI", "UV_210nm", "UV_254nm"]:
        raise ValueError("Expected RI, 210 nm, and 254 nm detector channels.")
    return channels


def filter_peaks(peaks, start, end, min_area=1000.0, min_relative_area_percent=1.0):
    """Filter saved peak records, retaining their original areas and bounds.

    Relative reference is the largest positive saved area in this file/detector's
    requested apex window. This is a reporting filter, not peak deconvolution.
    """
    if not math.isfinite(start) or not math.isfinite(end) or start >= end:
        raise ValueError("Window bounds must be finite, with start < end.")
    if not math.isfinite(min_area) or min_area < 0:
        raise ValueError("Minimum area must be finite and nonnegative (uV*s).")
    if not math.isfinite(min_relative_area_percent) or not 0 <= min_relative_area_percent <= 100:
        raise ValueError("Minimum relative area must be between 0 and 100 percent.")
    candidates = [p for p in peaks if start <= p["retention_time_min"] <= end and p["area_uV_s"] > 0]
    reference = max((p["area_uV_s"] for p in candidates), default=0.0)
    threshold = max(min_area, reference * min_relative_area_percent / 100)
    return [p for p in candidates if p["area_uV_s"] >= threshold], threshold, reference


def select_main_peak(peaks, start, end, min_area=0.0, min_relative_area_percent=0.0):
    candidates, _, _ = filter_peaks(peaks, start, end, min_area, min_relative_area_percent)
    return max(candidates, key=lambda p: p["area_uV_s"], default=None), len(candidates)


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def extract_folder(folder, output, start=6.0, end=12.0, min_area=1000.0, min_relative_area_percent=1.0):
    filter_peaks([], start, end, min_area, min_relative_area_percent)
    files = sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".lcd"], key=lambda p: natural_key(p.name))
    if not files:
        raise ValueError("No LCD files found in the input folder.")
    output.mkdir(parents=True, exist_ok=True)
    all_rows, filtered_rows, summaries, manifest = [], [], [], []
    for path in files:
        summary = {"filename": path.name, "selection_start_min": start, "selection_end_min": end,
                   "min_area_uV_s": min_area, "min_relative_area_percent": min_relative_area_percent}
        entry = {"filename": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        # Errors remain explicit rows; no failed file is silently skipped.
        try:
            channels = read_saved_peaks(path)
            for channel in channels:
                for peak in channel["peaks"]:
                    all_rows.append({"filename": path.name, "detector": channel["detector"],
                                     "channel_id": channel["channel_id"], **peak, "source": "Shimadzu saved peak table"})
                filtered, threshold, reference = filter_peaks(channel["peaks"], start, end, min_area, min_relative_area_percent)
                for peak in filtered:
                    filtered_rows.append({"filename": path.name, "detector": channel["detector"],
                                          "channel_id": channel["channel_id"], **peak,
                                          "source": "Shimadzu saved peak table",
                                          "area_threshold_uV_s": threshold,
                                          "relative_area_percent": peak["area_uV_s"] / reference * 100})
                main, candidate_count = select_main_peak(filtered, start, end)
                prefix = channel["key"]
                summary[prefix + "_saved_peak_count"] = len(channel["peaks"])
                summary[prefix + "_window_candidate_count"] = candidate_count
                summary[prefix + "_area_threshold_uV_s"] = threshold
                in_window = any(start <= p["retention_time_min"] <= end and p["area_uV_s"] > 0 for p in channel["peaks"])
                missing_status = "all_window_peaks_below_threshold" if in_window else "no_positive_peak_in_window"
                summary[prefix + "_status"] = "ok" if main else (channel["status"] if channel["status"] != "ok" else missing_status)
                for field in ["area_uV_s", "retention_time_min", "height_uV", "start_min", "end_min", "peak_number"]:
                    summary[prefix + "_" + field] = main[field] if main else ""
            summary["status"] = "ok"
            summary["error"] = ""
            entry["channels"] = [{k: v for k, v in c.items() if k != "peaks"} | {"peak_count": len(c["peaks"])} for c in channels]
        except (OSError, ValueError, AssertionError, struct.error) as error:
            summary["status"], summary["error"] = "error", f"{type(error).__name__}: {error}"
        entry["status"] = summary["status"]
        manifest.append(entry)
        summaries.append(summary)
    all_fields = ["filename", "detector", "channel_id", "peak_number", "retention_time_min", "area_uV_s", "height_uV", "start_min", "end_min", "source"]
    summary_fields = ["filename", "selection_start_min", "selection_end_min", "min_area_uV_s", "min_relative_area_percent"]
    for key in ["RI", "UV_210nm", "UV_254nm"]:
        summary_fields.extend(key + "_" + field for field in ["area_uV_s", "retention_time_min", "height_uV", "start_min", "end_min", "peak_number", "saved_peak_count", "window_candidate_count", "area_threshold_uV_s", "status"])
    summary_fields.extend(["status", "error"])
    write_csv(output / "main_peak_areas.csv", summaries, summary_fields)
    write_csv(output / "all_saved_peak_areas.csv", all_rows, all_fields)
    write_csv(output / "large_peak_areas.csv", filtered_rows, all_fields + ["area_threshold_uV_s", "relative_area_percent"])
    metadata = {
        "input_folder": str(folder.resolve()), "file_count": len(files), "saved_peak_count": len(all_rows),
        "failed_files": sum(row["status"] == "error" for row in summaries),
        "filtered_peak_count": len(filtered_rows),
        "filters": {"min_area_uV_s": min_area, "min_relative_area_percent": min_relative_area_percent,
                    "relative_reference": "Largest positive saved peak within the apex window, separately per file and detector.",
                    "effective_threshold": "max(min_area_uV_s, reference_area_uV_s * min_relative_area_percent / 100)",
                    "note": "Default 1000 uV*s matches the screenshot's minimum-area value; the additional 1% relative filter is a stricter reporting choice, not a reproduction of its inactive relative-area control."},
        "method": "Read stored Shimadzu VER1 PT-* peak tables without reintegration or area scaling.",
        "area_unit": "uV*s", "height_unit": "uV", "time_unit": "min",
        "summary_rule": f"Largest saved area passing the area filters with retention time in [{start}, {end}] min, separately for each detector. Window filters the apex; saved integration start/end bounds are preserved.",
        "missing_values": "Blank area means no qualifying saved peak/table or a file error; never replaced with zero.",
        "format_reference": "https://github.com/ethanbass/chromConverter/blob/master/R/read_shimadzu_peaktable.R",
        "files": manifest,
    }
    (output / "extraction_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Processed {len(files)} LCD files; exported {len(all_rows)} saved peaks; {metadata['failed_files']} file errors.")
    print(f"Main peak summary: {(output / 'main_peak_areas.csv').resolve()}")
    print(f"All saved peaks: {(output / 'all_saved_peak_areas.csv').resolve()}")
    print(f"Large peaks: {len(filtered_rows)} retained; {(output / 'large_peak_areas.csv').resolve()}")
    return summaries, all_rows, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", nargs="?", type=Path, default=DEFAULT_SOURCE.parent)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "batch_results" / "26_10_22_47A1-2_filtered")
    parser.add_argument("--start", type=float, default=6)
    parser.add_argument("--end", type=float, default=12)
    parser.add_argument("--min-area", type=float, default=1000, help="Minimum saved area in uV*s (default: 1000)")
    parser.add_argument("--min-relative-area-percent", type=float, default=1,
                        help="Minimum percent of largest positive peak per file/detector in the apex window; 0 disables (default: 1)")
    args = parser.parse_args()
    try:
        _, _, metadata = extract_folder(args.folder, args.output, args.start, args.end, args.min_area, args.min_relative_area_percent)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    if metadata["failed_files"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
