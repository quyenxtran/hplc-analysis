"""Fit an envelope without changing manual peaks, history, or raw measurements."""
from dataclasses import asdict
import hashlib
import numpy as np
import scipy
from scipy.stats import norm, exponnorm
from .setup import prepare
from .solver import solve
from .shapes import components
from .diagnostics import diagnostics
from .report import FitResult
from ..editing.model import trapezoids


class FitOps:
    def fit_components(self, peak_id, centers_min, model="gaussian", center_tolerance_min=None, starts=5):
        curve, x, y, guess, low, high, scale = prepare(
            self, peak_id, centers_min, model, center_tolerance_min, starts)
        peak = self._get(peak_id)
        a, b = peak.start_min, peak.end_min
        width = b - a
        best, solutions = solve((x - a) / width, y / scale, guess, low, high, model, starts)
        pars = best.x.reshape(guess.shape)
        values = components((x - a) / width, pars, model)
        info, stderr = diagnostics(best, solutions, values, y / scale, low, high)
        errors = stderr.reshape(guess.shape) if stderr is not None else None
        rows = []
        for i, p in enumerate(pars):
            area, mu, sigma = p[:3]
            distribution = norm(loc=mu, scale=sigma) if model == "gaussian" else exponnorm(p[3] / sigma, loc=mu, scale=sigma)
            fraction = float(distribution.cdf(1) - distribution.cdf(0))
            full_area = float(area * width * scale * 60000)
            if fraction < 0.95 and "truncated_components" not in info["flags"]:
                info["flags"].append("truncated_components")
            if sigma * width < np.median(np.diff(x)) and "undersampled_component" not in info["flags"]:
                info["flags"].append("undersampled_component")
            grid = np.linspace(0, 1, 5001)
            apex = float(a + width * grid[np.argmax(components(grid, [p], model)[0])])
            rows.append({"component_id": f"component_{i + 1}", "model": model,
                         "location_min": float(a + mu * width), "apex_min": apex,
                         "sigma_min": float(sigma * width), "tau_min": float(p[3] * width) if model == "emg" else 0.0,
                         "area_window_uV_s": full_area * fraction, "area_full_model_uV_s": full_area,
                         "area_full_model_se_uV_s": float(errors[i, 0] * width * scale * 60000) if errors is not None else None,
                         "fraction_in_window": fraction})
        measured_area = trapezoids(curve["time_min"], curve["allocated_mv"]) * 60000
        fitted_area = sum(row["area_window_uV_s"] for row in rows)
        info.update(rmse_mv=info.pop("rmse_scaled") * scale, sample_count=len(x),
                    converged_starts=len(solutions), n_parameters=len(best.x),
                    measured_window_area_uV_s=measured_area, fitted_window_area_uV_s=fitted_area,
                    residual_area_uV_s=measured_area - fitted_area)
        info["flags"] = sorted(set(info["flags"]))
        raw = self.time_min.astype("<f8").tobytes() + self.signal_mv.astype("<f8").tobytes()
        output = {"time_min": x, "signal_mV": np.interp(x, self.time_min, self.signal_mv),
                  "baseline_mV": np.interp(x, peak.baseline_times, peak.baseline_values_mv),
                  "fitted_net_mV": values.sum(axis=0) * scale, "residual_mV": y - values.sum(axis=0) * scale}
        output.update({f"component_{i + 1}_mV": v * scale for i, v in enumerate(values)})
        return FitResult({"schema_version": 1, "label": self.label, "trace_sha256": hashlib.sha256(raw).hexdigest(),
                          "time_unit": "min", "signal_unit": "mV", "area_unit": "uV*s",
                          "numpy_version": np.__version__, "scipy_version": scipy.__version__,
                          "peak": asdict(peak), "editing_history": self.history,
                          "configuration": {"model": model, "centers_min": list(map(float, centers_min)),
                                            "center_tolerance_min": center_tolerance_min, "starts": starts},
                          "assumptions": "Positive model components; fixed reviewed baseline; unweighted least squares on original samples. Full areas extrapolate tails. SE is local, conditional on model/count/baseline and independent equal-variance noise; not proof of chemical identity.",
                          "components": rows, "diagnostics": info}, output)
