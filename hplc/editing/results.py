"""Peak editing: results."""
import numpy as np
from .model import trapezoids

class ResultOps:
    def curve(self, peak_id, state=None):
        state = self._peaks if state is None else state
        if peak_id not in state:
            raise ValueError(f"Unknown peak: {peak_id}")
        peak = state[peak_id]
        children = [p for p in state.values() if p.parent_id == peak_id]
        breaks = sorted({peak.start_min, peak.end_min, *(t for p in children for t in (p.start_min, p.end_min))})
        times, signals, baselines, allocated = [], [], [], []
        for a, b in zip(breaks, breaks[1:]):
            knots = [*peak.baseline_times, *(t for p in children for t in p.baseline_times)]
            x = np.unique([a, b, *self.time_min[(self.time_min > a) & (self.time_min < b)], *(t for t in knots if a < t < b)])
            y = np.interp(x, self.time_min, self.signal_mv)
            base = np.interp(x, peak.baseline_times, peak.baseline_values_mv)
            net = y - base
            for child in children:
                if child.start_min < (a + b) / 2 < child.end_min:
                    net = net - (y - np.interp(x, child.baseline_times, child.baseline_values_mv))
            times.extend(x)
            signals.extend(y)
            baselines.extend(base)
            allocated.extend(net)
        # Duplicate times at skim boundaries encode jumps with zero-width steps,
        # ensuring the exported allocated curve integrates to the reported area.
        return {"time_min": np.asarray(times), "signal_mv": np.asarray(signals),
                "baseline_mv": np.asarray(baselines), "allocated_mv": np.asarray(allocated)}

    def peak_table(self, include_rejected=False, state=None):
        state = self._peaks if state is None else state
        rows = []
        for peak in sorted(state.values(), key=lambda p: (p.start_min, p.end_min, p.peak_id)):
            if not peak.enabled and not include_rejected:
                continue
            curve = self.curve(peak.peak_id, state)
            x, y, base, net = (curve[key] for key in ("time_min", "signal_mv", "baseline_mv", "allocated_mv"))
            area = trapezoids(x, net)
            gross = trapezoids(x, y - base)
            flags = []
            if np.min(y - base) < -1e-9:
                flags.append("baseline_crosses_signal")
            if area <= 0:
                flags.append("nonpositive_area")
            if np.min(net) < -1e-9 and any(p.parent_id == peak.peak_id for p in state.values()):
                flags.append("skim_below_parent_baseline")
            if abs(peak.start_min - self.time_min[0]) < 1e-12 or abs(peak.end_min - self.time_min[-1]) < 1e-12:
                flags.append("touches_acquisition_boundary")
            apex = int(np.argmax(net))
            rows.append({"peak_id": peak.peak_id, "status": "active" if peak.enabled else "rejected",
                         "parent_id": peak.parent_id, "method": peak.method,
                         "start_min": peak.start_min, "end_min": peak.end_min,
                         "retention_time_min": float(x[apex]), "height_uV": float(net[apex] * 1000),
                         "area_uV_s": area * 60000, "area_mV_min": area,
                         "envelope_area_uV_s": gross * 60000, "skim_deduction_uV_s": (gross - area) * 60000,
                         "flags": ";".join(flags)})
        return rows
