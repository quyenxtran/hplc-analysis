"""Batch CSV tables and method/provenance metadata."""
import json
from .csv_io import write_csv

def finish_export(folder, output, files, summaries, all_rows, filtered_rows, manifest, start, end, min_area, min_relative_area_percent, min_retention_time):
    effective_start = max(start, min_retention_time)
    all_fields = ["filename", "detector", "channel_id", "peak_number", "retention_time_min", "area_uV_s", "height_uV", "start_min", "end_min", "source"]
    summary_fields = ["filename", "selection_start_min", "selection_end_min", "min_area_uV_s", "min_relative_area_percent", "min_retention_time_min"]
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
                    "min_retention_time_min": min_retention_time, "effective_start_min": effective_start,
                    "relative_reference": "Largest positive saved peak within the apex window, separately per file and detector.",
                    "effective_threshold": "max(min_area_uV_s, reference_area_uV_s * min_relative_area_percent / 100)",
                    "note": "Default 1000 uV*s matches the screenshot's minimum-area value; the additional 1% relative filter is a stricter reporting choice, not a reproduction of its inactive relative-area control."},
        "method": "Read stored Shimadzu VER1 PT-* peak tables without reintegration or area scaling.",
        "area_unit": "uV*s", "height_unit": "uV", "time_unit": "min",
        "summary_rule": f"Largest saved area passing the area filters with retention time in [{effective_start}, {end}] min (requested start {start}, minimum retention time {min_retention_time}), separately for each detector. Window filters the apex; saved integration start/end bounds are preserved.",
        "missing_values": "Blank area means no qualifying saved peak/table or a file error; never replaced with zero.",
        "format_reference": "https://github.com/ethanbass/chromConverter/blob/master/R/read_shimadzu_peaktable.R",
        "files": manifest,
    }
    (output / "extraction_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Processed {len(files)} LCD files; exported {len(all_rows)} saved peaks; {metadata['failed_files']} file errors.")
    print(f"Main peak summary: {(output / 'main_peak_areas.csv').resolve()}")
    print(f"All saved peaks: {(output / 'all_saved_peak_areas.csv').resolve()}")
    print(f"Large peaks: {len(filtered_rows)} retained; {(output / 'large_peak_areas.csv').resolve()}")
    return metadata
