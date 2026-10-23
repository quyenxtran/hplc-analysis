"""Validate fit requests and construct ordered center/width bounds."""
import numpy as np
from ..editing.model import trapezoids


def prepare(editor, peak_id, centers_min, model, center_tolerance_min, starts):
    peak = editor._get(peak_id)
    editor._no_skims(peak)
    if model not in ("gaussian", "emg"):
        raise ValueError("Model must be gaussian or emg.")
    if isinstance(starts, bool) or not isinstance(starts, int) or not 1 <= starts <= 20:
        raise ValueError("Use 1 to 20 deterministic starting points.")
    centers = np.asarray(centers_min, dtype=float)
    if centers.ndim != 1 or not 1 <= len(centers) <= 6 or not np.all(np.isfinite(centers)):
        raise ValueError("Supply 1 to 6 finite center estimates in minutes.")
    a, b = peak.start_min, peak.end_min
    if np.any(np.diff(centers) <= 0) or not a < centers[0] <= centers[-1] < b:
        raise ValueError("Center estimates must increase strictly inside the peak window.")
    curve = editor.curve(peak_id)
    x = editor.time_min[(editor.time_min >= a) & (editor.time_min <= b)]
    y = np.interp(x, curve["time_min"], curve["allocated_mv"])
    if len(x) < 2:
        raise ValueError("Window contains too few original samples to fit.")
    width, scale = b - a, float(np.max(y))
    count = 3 if model == "gaussian" else 4
    if len(x) <= count * len(centers) + 2 or scale <= 0:
        raise ValueError("Need positive signal and more independent samples than fit parameters.")
    dx = float(np.median(np.diff(x))) / width
    min_sigma = max(dx / 2, 1e-5)
    if min_sigma >= 0.25:
        raise ValueError("Window has insufficient time resolution.")
    c = (centers - a) / width
    edges = np.r_[0, (c[:-1] + c[1:]) / 2, 1]
    tolerance = 1.0
    if center_tolerance_min is not None:
        tolerance = editor._number(center_tolerance_min, "Center tolerance") / width
        if tolerance <= 0:
            raise ValueError("Center tolerance must be positive.")
    low, high, guess = [], [], []
    total = max(trapezoids(x, np.maximum(y, 0)) / (width * scale), 1e-6)
    for i, center in enumerate(c):
        lo, hi = max(edges[i], center - tolerance), min(edges[i + 1], center + tolerance)
        if hi - lo < 1e-8:
            raise ValueError("Center bounds are too narrow; increase spacing or tolerance.")
        low.append([0, lo, min_sigma] + ([min_sigma / 10] if count == 4 else []))
        high.append([10, hi, 0.5] + ([1.0] if count == 4 else []))
        sigma = np.clip((edges[i + 1] - edges[i]) / 5, min_sigma * 1.1, 0.4)
        guess.append([total / len(c), center, sigma] + ([sigma] if count == 4 else []))
    return curve, x, y, np.asarray(guess), np.asarray(low), np.asarray(high), scale
