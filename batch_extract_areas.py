"""Export saved Shimadzu peak areas from a folder of LCD files.

Reads the vendor's PT-* peak tables; does not reintegrate raw chromatograms.
Writes every saved peak plus a wide summary selecting the largest positive-area
peak whose retention time falls within the requested window (default 6-12 min).
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


def select_main_peak(peaks, start, end):
    candidates = [p for p in peaks if start <= p["retention_time_min"] <= end and p["area_uV_s"] > 0]
    return max(candidates, key=lambda p: p["area_uV_s"], default=None), len(candidates)


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def extract_folder(folder, output, start=6.0, end=12.0):
    if not math.isfinite(start) or not math.isfinite(end) or start >= end:
        raise ValueError("Window bounds must be finite, with start < end.")
    files = sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".lcd"], key=lambda p: natural_key(p.name))
    if not files:
        raise ValueError("No LCD files found in the input folder.")
    output.mkdir(parents=True, exist_ok=True)
    all_rows, summaries, manifest = [], [], []
    for path in files:
        summary = {"filename": path.name, "selection_start_min": start, "selection_end_min": end}
        entry = {"filename": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        # Errors remain explicit rows; no failed file is silently skipped.
        try:
            channels = read_saved_peaks(path)
            for channel in channels:
                for peak in channel["peaks"]:
                    all_rows.append({"filename": path.name, "detector": channel["detector"],
                                     "channel_id": channel["channel_id"], **peak, "source": "Shimadzu saved peak table"})
                main, candidate_count = select_main_peak(channel["peaks"], start, end)
                prefix = channel["key"]
                summary[prefix + "_saved_peak_count"] = len(channel["peaks"])
                summary[prefix + "_window_candidate_count"] = candidate_count
                summary[prefix + "_status"] = "ok" if main else (channel["status"] if channel["status"] != "ok" else "no_positive_peak_in_window")
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
    summary_fields = ["filename", "selection_start_min", "selection_end_min"]
    for key in ["RI", "UV_210nm", "UV_254nm"]:
        summary_fields.extend(key + "_" + field for field in ["area_uV_s", "retention_time_min", "height_uV", "start_min", "end_min", "peak_number", "saved_peak_count", "window_candidate_count", "status"])
    summary_fields.extend(["status", "error"])
    write_csv(output / "main_peak_areas.csv", summaries, summary_fields)
    write_csv(output / "all_saved_peak_areas.csv", all_rows, all_fields)
    metadata = {
        "input_folder": str(folder.resolve()), "file_count": len(files), "saved_peak_count": len(all_rows),
        "failed_files": sum(row["status"] == "error" for row in summaries),
        "method": "Read stored Shimadzu VER1 PT-* peak tables without reintegration or area scaling.",
        "area_unit": "uV*s", "height_unit": "uV", "time_unit": "min",
        "summary_rule": f"Largest positive saved area with retention time in [{start}, {end}] min, separately for each detector. Window filters the apex; saved integration start/end bounds are preserved.",
        "missing_values": "Blank area means no qualifying saved peak/table or a file error; never replaced with zero.",
        "format_reference": "https://github.com/ethanbass/chromConverter/blob/master/R/read_shimadzu_peaktable.R",
        "files": manifest,
    }
    (output / "extraction_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Processed {len(files)} LCD files; exported {len(all_rows)} saved peaks; {metadata['failed_files']} file errors.")
    print(f"Main peak summary: {(output / 'main_peak_areas.csv').resolve()}")
    print(f"All saved peaks: {(output / 'all_saved_peak_areas.csv').resolve()}")
    return summaries, all_rows, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", nargs="?", type=Path, default=DEFAULT_SOURCE.parent)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "batch_results" / "26_10_22_47A1-2")
    parser.add_argument("--start", type=float, default=6)
    parser.add_argument("--end", type=float, default=12)
    args = parser.parse_args()
    try:
        _, _, metadata = extract_folder(args.folder, args.output, args.start, args.end)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    if metadata["failed_files"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
