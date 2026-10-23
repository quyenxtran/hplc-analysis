"""Peak editing: state."""
from copy import deepcopy
import math
import numpy as np

class EditorState:
    def __init__(self, time_min, signal_mv, label="Chromatogram"):
        x, y = np.array(time_min, dtype=float, copy=True), np.array(signal_mv, dtype=float, copy=True)
        if x.ndim != 1 or y.shape != x.shape or len(x) < 2:
            raise ValueError("Time and signal must be matching one-dimensional arrays with at least two points.")
        if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)) or not np.all(np.diff(x) > 0):
            raise ValueError("Trace values must be finite; times must strictly increase.")
        x.flags.writeable = y.flags.writeable = False
        self.time_min, self.signal_mv, self.label = x, y, str(label)
        self._peaks, self._undo, self._redo, self._history = {}, [], [], []

    @property
    def peaks(self):
        return dict(self._peaks)

    @property
    def history(self):
        return deepcopy(self._history)

    def snapshot(self):
        return dict(self._peaks)

    def _get(self, peak_id, enabled=True):
        if peak_id not in self._peaks:
            raise ValueError(f"Unknown peak: {peak_id}")
        peak = self._peaks[peak_id]
        if enabled and not peak.enabled:
            raise ValueError(f"Peak is rejected: {peak_id}")
        return peak

    def _new_id(self, peak_id):
        if not isinstance(peak_id, str) or not peak_id.strip() or peak_id in self._peaks:
            raise ValueError("Peak IDs must be nonempty and unique, including rejected peaks.")

    def _number(self, value, name):
        if isinstance(value, bool):
            raise ValueError(f"{name} must be a finite number.")
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be a finite number.") from None
        if not math.isfinite(number):
            raise ValueError(f"{name} must be a finite number.")
        return number

    def _bounds(self, start, end):
        start, end = self._number(start, "Start"), self._number(end, "End")
        if not self.time_min[0] <= start < end <= self.time_min[-1]:
            raise ValueError("Peak bounds must be ordered and inside the acquired time range.")
        return start, end
