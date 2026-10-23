"""Bounded, deterministic multistart least squares; no smoothing or clipping."""
import numpy as np
from scipy.optimize import least_squares
from .shapes import components


def solve(x, y, guess, low, high, model, starts):
    shape = guess.shape
    rng = np.random.default_rng(47)
    solutions = []
    for index in range(starts):
        initial = guess.copy()
        if index:
            initial[:, 0] *= rng.uniform(0.6, 1.4, shape[0])
            initial[:, 1] = low[:, 1] + rng.uniform(0.15, 0.85, shape[0]) * (high[:, 1] - low[:, 1])
            initial[:, 2:] *= rng.uniform(0.5, 1.6, initial[:, 2:].shape)
        initial = np.clip(initial, low + 1e-10, high - 1e-10)
        result = least_squares(
            lambda flat: components(x, flat.reshape(shape), model).sum(axis=0) - y,
            initial.ravel(), bounds=(low.ravel(), high.ravel()),
            x_scale="jac", max_nfev=2000, ftol=1e-10, xtol=1e-10, gtol=1e-10)
        if result.success and np.all(np.isfinite(result.x)):
            solutions.append(result)
    if not solutions:
        raise ValueError("Fit did not converge; revise centers, window, baseline, or component count.")
    solutions.sort(key=lambda r: r.cost)
    return solutions[0], solutions
