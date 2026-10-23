"""Explicit retention and area thresholds for saved peaks."""
import math

def filter_peaks(peaks, start, end, min_area=1000.0, min_relative_area_percent=1.0, min_retention_time=5.0):
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
    if not math.isfinite(min_retention_time) or min_retention_time < 0:
        raise ValueError("Minimum retention time must be finite and nonnegative (min).")
    effective_start = max(start, min_retention_time)
    candidates = [p for p in peaks if effective_start <= p["retention_time_min"] <= end and p["area_uV_s"] > 0]
    reference = max((p["area_uV_s"] for p in candidates), default=0.0)
    threshold = max(min_area, reference * min_relative_area_percent / 100)
    return [p for p in candidates if p["area_uV_s"] >= threshold], threshold, reference

def select_main_peak(peaks, start, end, min_area=0.0, min_relative_area_percent=0.0, min_retention_time=5.0):
    candidates, _, _ = filter_peaks(peaks, start, end, min_area, min_relative_area_percent, min_retention_time)
    return max(candidates, key=lambda p: p["area_uV_s"], default=None), len(candidates)
