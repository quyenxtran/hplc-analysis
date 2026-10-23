"""Peak editing: splitting."""
import numpy as np
from .model import Peak, json_value

class SplitOps:
    def split_n_peaks(self, peak_id, split_times, child_ids=None, separation="vertical"):
        peak = self._get(peak_id)
        self._no_skims(peak)
        cuts = [self._number(t, "Split time") for t in split_times]
        if not cuts or any(a >= b for a, b in zip(cuts, cuts[1:])) or not peak.start_min < cuts[0] <= cuts[-1] < peak.end_min:
            raise ValueError("Split times must be unique, increasing, and strictly inside the peak.")
        ids = list(child_ids) if child_ids is not None else [f"{peak_id}_{i + 1}" for i in range(len(cuts) + 1)]
        if len(ids) != len(cuts) + 1 or len(set(ids)) != len(ids):
            raise ValueError("Provide one unique child ID per split region.")
        for name in ids:
            self._new_id(name)
        if separation not in ("vertical", "baseline"):
            raise ValueError("Separation must be vertical or baseline.")
        state = self.snapshot()
        del state[peak_id]
        bounds = [peak.start_min, *cuts, peak.end_min]
        for index, name in enumerate(ids):
            a, b = bounds[index:index + 2]
            if separation == "vertical":
                times, values = peak.baseline_times, peak.baseline_values_mv
            else:
                left = float(np.interp(a, peak.baseline_times, peak.baseline_values_mv)) if index == 0 else float(np.interp(a, self.time_min, self.signal_mv))
                right = float(np.interp(b, peak.baseline_times, peak.baseline_values_mv)) if index == len(ids) - 1 else float(np.interp(b, self.time_min, self.signal_mv))
                times, values = (a, b), (left, right)
            state[name] = Peak(name, a, b, times, values, separation)
        self._commit("split_n_peaks", {"peak_id": peak_id, "split_times": cuts,
                                       "child_ids": ids, "separation": separation}, state)
        return ids

    def split_peak(self, peak_id, at_min, child_ids=None, separation="vertical"):
        return self.split_n_peaks(peak_id, [at_min], child_ids, separation)

    def find_valley(self, peak_id, between_min):
        """Find an actual local minimum of baseline-corrected signal in a bracket."""
        peak = self._get(peak_id)
        if len(between_min) != 2:
            raise ValueError("Valley bracket must contain two times.")
        a, b = self._bounds(*between_min)
        if not peak.start_min < a < b < peak.end_min:
            raise ValueError("Valley bracket must lie strictly inside the peak.")
        corrected = self.signal_mv - np.interp(self.time_min, peak.baseline_times, peak.baseline_values_mv)
        indexes = np.flatnonzero((self.time_min[1:-1] >= a) & (self.time_min[1:-1] <= b)
                                & (corrected[1:-1] <= corrected[:-2]) & (corrected[1:-1] <= corrected[2:])
                                & ((corrected[1:-1] < corrected[:-2]) | (corrected[1:-1] < corrected[2:]))) + 1
        if not len(indexes):
            raise ValueError("No local valley found in bracket; choose an explicit cut or a skim.")
        index = min(indexes, key=lambda i: (corrected[i], abs(self.time_min[i] - (a + b) / 2)))
        return float(self.time_min[index])

    def split_at_valley(self, peak_id, between_min, child_ids=None, separation="vertical"):
        cut = self.find_valley(peak_id, between_min)
        ids = self.split_peak(peak_id, cut, child_ids, separation)
        self._history[-1]["operation"] = "split_at_valley"
        self._history[-1]["parameters"] = {"peak_id": peak_id, "between_min": json_value(between_min),
                                             "child_ids": ids, "separation": separation}
        self._history[-1]["resolved_split_min"] = cut
        return ids
