"""Conditional uncertainty and identifiability checks for fitted mixtures."""
import numpy as np


def diagnostics(best, solutions, curves, net, low, high):
    flags = []
    jac = best.jac
    norms = np.linalg.norm(jac, axis=0)
    singular = np.linalg.svd(jac / np.maximum(norms, 1e-30), compute_uv=False)
    condition = float(singular[0] / max(singular[-1], 1e-30))
    weak = condition > 1e6 or np.any(norms < 1e-12)
    if weak:
        flags.append("weak_identifiability")
    stderr = None
    if not weak and len(net) > len(best.x):
        covariance = np.linalg.pinv(jac.T @ jac, rcond=1e-14) * (2 * best.cost / (len(net) - len(best.x)))
        stderr = np.sqrt(np.maximum(np.diag(covariance), 0))
    if np.any(best.active_mask):
        flags.append("parameter_at_bound")
    if len(curves) > 1:
        similarity = np.corrcoef(curves)
        if np.any(similarity[np.triu_indices(len(curves), 1)] > 0.995):
            flags.append("high_component_overlap")
    count = len(curves)
    step = len(best.x) // count
    areas = best.x.reshape(count, step)[:, 0]
    if stderr is not None and np.any(stderr[::step] > 0.05 * np.maximum(areas, 1e-8)):
        flags.append("large_conditional_area_uncertainty")
    threshold = max(best.cost * 1.05, len(net) * 1e-10)
    for other in solutions[1:]:
        other_areas = other.x.reshape(count, step)[:, 0]
        if other.cost <= threshold and np.any(np.abs(other_areas - areas) > 0.2 * np.maximum(areas, 1e-8)):
            flags.append("alternative_area_solutions")
            break
    residual = net - curves.sum(axis=0)
    rmse = float(np.sqrt(np.mean(residual ** 2)))
    if rmse > 0.05 * max(float(np.ptp(net)), 1e-12):
        flags.append("poor_fit")
    if any(flag in flags for flag in ("high_component_overlap", "alternative_area_solutions", "parameter_at_bound")):
        stderr = None
    return {"flags": flags, "scaled_jacobian_condition": condition, "rmse_scaled": rmse}, stderr
