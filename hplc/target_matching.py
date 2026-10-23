"""Conservative target assignment and exploratory late-peak filtering."""
from .targets import finite_number, MATCH_FIELDS

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
