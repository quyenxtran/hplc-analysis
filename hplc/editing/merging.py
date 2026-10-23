"""Peak editing: merging."""
from dataclasses import replace
import numpy as np
from .model import Peak

class MergeOps:
    def unify_peaks(self, peak_ids, new_id, baseline="outer"):
        if len(peak_ids) < 2 or len(set(peak_ids)) != len(peak_ids):
            raise ValueError("Select at least two distinct peaks to unify.")
        peaks = sorted((self._get(name) for name in peak_ids), key=lambda p: p.start_min)
        for peak in peaks:
            self._no_skims(peak)
        self._new_id(new_id)
        if baseline not in ("outer", "preserve"):
            raise ValueError("Unification baseline must be outer or preserve.")
        start, end = peaks[0].start_min, peaks[-1].end_min
        others = [p for p in self._peaks.values() if p.enabled and not p.parent_id and p.peak_id not in peak_ids]
        if any(p.start_min < end and p.end_min > start for p in others):
            raise ValueError("An unselected active peak lies inside the merge interval.")
        if baseline == "preserve":
            reference = peaks[0]
            if any(p.baseline_times != reference.baseline_times or p.baseline_values_mv != reference.baseline_values_mv for p in peaks):
                raise ValueError("Preserve mode requires exactly the same baseline curve on all peaks.")
            if any(abs(a.end_min - b.start_min) > 1e-12 for a, b in zip(peaks, peaks[1:])):
                raise ValueError("Preserve mode requires contiguous windows.")
            times, values = reference.baseline_times, reference.baseline_values_mv
        else:
            times = (start, end)
            values = (float(np.interp(start, peaks[0].baseline_times, peaks[0].baseline_values_mv)),
                      float(np.interp(end, peaks[-1].baseline_times, peaks[-1].baseline_values_mv)))
        state = self.snapshot()
        for name in peak_ids:
            del state[name]
        state[new_id] = Peak(new_id, start, end, times, values, "unified_" + baseline)
        self._commit("unify_peaks", {"peak_ids": list(peak_ids), "new_id": new_id, "baseline": baseline}, state)
        return new_id

    def set_separation(self, left_id, right_id, mode="vertical", at_min=None):
        left, right = self._get(left_id), self._get(right_id)
        for peak in (left, right):
            self._no_skims(peak)
        if abs(left.end_min - right.start_min) > 1e-12:
            raise ValueError("Separation requires two adjacent windows in left-to-right order.")
        cut = left.end_min if at_min is None else self._number(at_min, "Separation time")
        if not left.start_min < cut < right.end_min or mode not in ("vertical", "baseline"):
            raise ValueError("Choose an internal separation time and vertical/baseline mode.")
        outer_times = (left.start_min, right.end_min)
        outer_values = (float(np.interp(left.start_min, left.baseline_times, left.baseline_values_mv)),
                        float(np.interp(right.end_min, right.baseline_times, right.baseline_values_mv)))
        valley_value = float(np.interp(cut, self.time_min, self.signal_mv))
        state = self.snapshot()
        if mode == "vertical":
            state[left_id] = replace(left, end_min=cut, baseline_times=outer_times, baseline_values_mv=outer_values, method=mode)
            state[right_id] = replace(right, start_min=cut, baseline_times=outer_times, baseline_values_mv=outer_values, method=mode)
        else:
            state[left_id] = replace(left, end_min=cut, baseline_times=(left.start_min, cut), baseline_values_mv=(outer_values[0], valley_value), method=mode)
            state[right_id] = replace(right, start_min=cut, baseline_times=(cut, right.end_min), baseline_values_mv=(valley_value, outer_values[1]), method=mode)
        self._commit("set_separation", {"left_id": left_id, "right_id": right_id, "mode": mode, "at_min": cut}, state)
