"""Peak editing: skimming."""
from dataclasses import replace
from .model import Peak

class SkimOps:
    def reject_peak(self, peak_id):
        peak = self._get(peak_id)
        state = self.snapshot()
        state[peak_id] = replace(peak, enabled=False)
        for child in tuple(state.values()):
            if child.parent_id == peak_id:
                state[child.peak_id] = replace(child, enabled=False)
        self._commit("reject_peak", {"peak_id": peak_id}, state)

    def restore_peak(self, peak_id):
        peak = self._get(peak_id, enabled=False)
        if peak.enabled:
            raise ValueError("Peak is already active.")
        state = self.snapshot()
        state[peak_id] = replace(peak, enabled=True)
        self._commit("restore_peak", {"peak_id": peak_id}, state)

    def skim_peak(self, parent_id, peak_id, start_min, end_min, baseline="linear", start_mv=None, end_mv=None, knots=None):
        """Allocate a rider peak above a user-defined skim baseline.

        The rider's signed area is subtracted from its host, conserving the
        combined assigned area. Linear endpoint skims work on either a tail or
        leading edge. Custom knots permit a manually specified curved baseline.
        This does not fit an exponential tail or infer pure component shapes.
        """
        parent = self._get(parent_id)
        if parent.parent_id:
            raise ValueError("Nested skims are unsupported.")
        self._new_id(peak_id)
        start, end = self._bounds(start_min, end_min)
        times, values = self._baseline(start, end, baseline, start_mv, end_mv, knots)
        state = self.snapshot()
        state[peak_id] = Peak(peak_id, start, end, times, values, "skim_" + baseline, parent_id=parent_id)
        self._commit("skim_peak", {"parent_id": parent_id, "peak_id": peak_id, "start_min": start,
                                   "end_min": end, "baseline": baseline, "start_mv": start_mv,
                                   "end_mv": end_mv, "knots": knots}, state)
        return peak_id

    def remove_skim(self, peak_id):
        peak = self._get(peak_id, enabled=False)
        if not peak.parent_id:
            raise ValueError("Peak is not a skim allocation.")
        state = self.snapshot()
        del state[peak_id]
        self._commit("remove_skim", {"peak_id": peak_id}, state)
