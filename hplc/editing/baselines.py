"""Peak editing: baselines."""
import numpy as np

class BaselineOps:
    def _baseline(self, start, end, mode="linear", start_mv=None, end_mv=None, knots=None):
        if mode == "custom":
            if knots is None or len(knots) < 2:
                raise ValueError("Custom baseline needs at least two [time_min, value_mV] knots.")
            points = [(self._number(t, "Baseline time"), self._number(v, "Baseline value")) for t, v in knots]
            if any(points[i][0] >= points[i + 1][0] for i in range(len(points) - 1)):
                raise ValueError("Custom baseline times must strictly increase.")
            if points[0][0] > start or points[-1][0] < end:
                raise ValueError("Baseline knots must cover the entire peak window.")
            if points[0][0] < self.time_min[0] or points[-1][0] > self.time_min[-1]:
                raise ValueError("Baseline knots must be inside the acquired range.")
            return tuple(t for t, _ in points), tuple(v for _, v in points)
        if knots is not None:
            raise ValueError("Knots are only valid with a custom baseline.")
        left = float(np.interp(start, self.time_min, self.signal_mv)) if start_mv is None else self._number(start_mv, "Start baseline")
        right = float(np.interp(end, self.time_min, self.signal_mv)) if end_mv is None else self._number(end_mv, "End baseline")
        if mode == "horizontal":
            if end_mv is not None and right != left:
                raise ValueError("Horizontal baseline endpoints must have the same value.")
            right = left
        elif mode == "zero":
            if start_mv is not None or end_mv is not None:
                raise ValueError("Zero baseline does not accept endpoint values.")
            left = right = 0.0
        elif mode != "linear":
            raise ValueError("Baseline must be linear, horizontal, zero, or custom.")
        return (start, end), (left, right)
