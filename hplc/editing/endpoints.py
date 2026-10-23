"""Peak editing: endpoints."""
from dataclasses import replace
import numpy as np
from .model import Peak

class EndpointOps:
    def insert_peak(self, peak_id, start_min, end_min, baseline="linear", start_mv=None, end_mv=None, knots=None):
        self._new_id(peak_id)
        start, end = self._bounds(start_min, end_min)
        times, values = self._baseline(start, end, baseline, start_mv, end_mv, knots)
        state = self.snapshot()
        state[peak_id] = Peak(peak_id, start, end, times, values, baseline)
        self._commit("insert_peak", {"peak_id": peak_id, "start_min": start, "end_min": end,
                                     "baseline": baseline, "start_mv": start_mv, "end_mv": end_mv, "knots": knots}, state)
        return peak_id

    def set_baseline(self, peak_id, mode="linear", start_mv=None, end_mv=None, knots=None):
        peak = self._get(peak_id)
        times, values = self._baseline(peak.start_min, peak.end_min, mode, start_mv, end_mv, knots)
        state = self.snapshot()
        state[peak_id] = replace(peak, baseline_times=times, baseline_values_mv=values, method=mode)
        self._commit("set_baseline", {"peak_id": peak_id, "mode": mode, "start_mv": start_mv,
                                      "end_mv": end_mv, "knots": knots}, state)

    def move_baseline(self, peak_id, start_min=None, end_min=None, start_mv=None, end_mv=None):
        """Move time/intensity endpoints, replacing any custom curve with a line.

        A moved time without an explicit intensity snaps that endpoint to the
        trace. Unmoved endpoints retain their existing baseline intensity.
        """
        peak = self._get(peak_id)
        if all(v is None for v in (start_min, end_min, start_mv, end_mv)):
            raise ValueError("Specify at least one endpoint adjustment.")
        start, end = self._bounds(peak.start_min if start_min is None else start_min,
                                  peak.end_min if end_min is None else end_min)
        left = start_mv if start_mv is not None else (float(np.interp(start, peak.baseline_times, peak.baseline_values_mv)) if start_min is None else None)
        right = end_mv if end_mv is not None else (float(np.interp(end, peak.baseline_times, peak.baseline_values_mv)) if end_min is None else None)
        times, values = self._baseline(start, end, "linear", left, right)
        state = self.snapshot()
        state[peak_id] = replace(peak, start_min=start, end_min=end, baseline_times=times,
                                baseline_values_mv=values, method="manual_endpoints")
        self._commit("move_baseline", {"peak_id": peak_id, "start_min": start_min, "end_min": end_min,
                                      "start_mv": start_mv, "end_mv": end_mv}, state)
