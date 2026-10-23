"""Signed numerical integration and calibrated input."""
import numpy as np
from .lcd import read_chromatograms

def area_to_uv_seconds(area_mv_min):
    """Convert mV*min to uV*s: 1000 uV/mV times 60 s/min."""
    return area_mv_min * 60_000

def integrate_window(time, signal, start, end, baseline="linear"):
    """Signed trapezoidal area with interpolated boundary samples, no clipping.

    Returns raw area, baseline area and net area in signal units times minutes.
    With linear baseline, net is the area above the endpoint-to-endpoint line.
    """
    time, signal = np.asarray(time, dtype=float), np.asarray(signal, dtype=float)
    if time.ndim != 1 or signal.shape != time.shape or len(time) < 2:
        raise ValueError("Time and signal must be matching 1D arrays with at least two samples.")
    if not np.all(np.isfinite(time)) or not np.all(np.isfinite(signal)):
        raise ValueError("Time and signal must contain only finite values.")
    if not np.all(np.diff(time) > 0):
        raise ValueError("Time must be strictly increasing, with no duplicates.")
    if not np.isfinite(start) or not np.isfinite(end) or start >= end:
        raise ValueError("Bounds must be finite and start must be less than end.")
    if start < time[0] or end > time[-1]:
        raise ValueError(f"Window [{start}, {end}] lies outside sampled range [{time[0]}, {time[-1]}] min.")
    if baseline not in ("linear", "none"):
        raise ValueError("Baseline must be 'linear' or 'none'.")
    inside = (time > start) & (time < end)
    x = np.concatenate(([start], time[inside], [end]))
    y = np.interp(x, time, signal)
    base = np.interp(x, [start, end], [y[0], y[-1]]) if baseline == "linear" else np.zeros_like(y)
    corrected = y - base
    # Explicit trapezoids support both older and newer NumPy installations.
    raw_area = float(np.sum(np.diff(x) * (y[:-1] + y[1:]) / 2))
    baseline_area = float(np.sum(np.diff(x) * (base[:-1] + base[1:]) / 2))
    net_area = float(np.sum(np.diff(x) * (corrected[:-1] + corrected[1:]) / 2))
    apex = int(np.argmax(corrected))
    return {
        "time": x, "signal": y, "baseline": base, "corrected": corrected,
        "raw_area": raw_area, "baseline_area": baseline_area, "net_area": net_area,
        "apex_time_min": float(x[apex]), "height_above_baseline": float(corrected[apex]),
    }

def load_channels(source):
    if source.suffix.lower() == ".lcd":
        return read_chromatograms(source)
    if source.suffix.lower() != ".csv":
        raise ValueError("Input must be .lcd or the CSV exported by plot_hplc.py.")
    data = np.genfromtxt(source, delimiter=",", names=True, encoding="utf-8-sig")
    expected = ["time_min", "RI_mV", "UV_210nm_mV", "UV_254nm_mV"]
    if data.dtype.names is None or any(key not in data.dtype.names for key in expected):
        raise ValueError(f"CSV must have columns: {', '.join(expected)}")
    return [
        {"channel": i, "label": label, "unit": "mV", "time": data["time_min"], "signal": data[column]}
        for i, (label, column) in enumerate([
            ("Refractive index", "RI_mV"), ("UV at 210 nm", "UV_210nm_mV"), ("UV at 254 nm", "UV_254nm_mV")
        ], 1)
    ]
