"""Area summary fields and unit conversion."""
from .integration import area_to_uv_seconds

def area_rows(channels, results, start, end, baseline):
    rows = []
    for channel, result in zip(channels, results):
        rows.append({
            "channel": channel["channel"], "detector": channel["label"], "signal_unit": channel["unit"],
            "start_min": start, "end_min": end, "baseline_method": baseline,
            "net_area_uV_s": area_to_uv_seconds(result["net_area"]),
            "raw_area_uV_s": area_to_uv_seconds(result["raw_area"]),
            "baseline_area_uV_s": area_to_uv_seconds(result["baseline_area"]),
            "height_above_baseline_uV": result["height_above_baseline"] * 1000,
            "raw_area_mV_min": result["raw_area"], "baseline_area_mV_min": result["baseline_area"],
            "net_area_mV_min": result["net_area"], "net_area_mV_s": result["net_area"] * 60,
            "apex_time_min": result["apex_time_min"], "height_above_baseline_mV": result["height_above_baseline"],
            "baseline_start_mV": float(result["baseline"][0]), "baseline_end_mV": float(result["baseline"][-1]),
        })
    return rows
