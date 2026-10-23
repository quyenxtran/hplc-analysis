"""Extract/filter one LCD with explicit per-file statuses."""
import hashlib
import struct
from .saved_peaks import read_saved_peaks
from .filters import filter_peaks, select_main_peak

def process_file(path, start, end, min_area, min_relative_area_percent, min_retention_time):
    effective_start = max(start, min_retention_time)
    all_rows, filtered_rows = [], []
    summary = {"filename": path.name, "selection_start_min": start, "selection_end_min": end,
               "min_area_uV_s": min_area, "min_relative_area_percent": min_relative_area_percent,
               "min_retention_time_min": min_retention_time}
    entry = {"filename": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    # Errors remain explicit rows; no failed file is silently skipped.
    try:
        channels = read_saved_peaks(path)
        for channel in channels:
            for peak in channel["peaks"]:
                all_rows.append({"filename": path.name, "detector": channel["detector"],
                                 "channel_id": channel["channel_id"], **peak, "source": "Shimadzu saved peak table"})
            filtered, threshold, reference = filter_peaks(channel["peaks"], start, end, min_area, min_relative_area_percent, min_retention_time)
            for peak in filtered:
                filtered_rows.append({"filename": path.name, "detector": channel["detector"],
                                      "channel_id": channel["channel_id"], **peak,
                                      "source": "Shimadzu saved peak table",
                                      "area_threshold_uV_s": threshold,
                                      "relative_area_percent": peak["area_uV_s"] / reference * 100})
            main, candidate_count = select_main_peak(filtered, start, end, min_retention_time=min_retention_time)
            prefix = channel["key"]
            summary[prefix + "_saved_peak_count"] = len(channel["peaks"])
            summary[prefix + "_window_candidate_count"] = candidate_count
            summary[prefix + "_area_threshold_uV_s"] = threshold
            in_window = any(effective_start <= p["retention_time_min"] <= end and p["area_uV_s"] > 0 for p in channel["peaks"])
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
    return summary, entry, all_rows, filtered_rows
