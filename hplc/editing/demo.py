"""Clearly labeled synthetic three-peak editing example."""
import numpy as np

def demo_trace_and_recipe():
    time = np.linspace(5, 9, 2401)
    baseline = 0.1 + 0.025 * (time - 5)
    signal = baseline.copy()
    for height, center, width in [(1.8, 6.4, 0.12), (1.4, 6.86, 0.16), (0.9, 7.35, 0.13)]:
        signal += height * np.exp(-0.5 * ((time - center) / width) ** 2)
    recipe = {
        "schema_version": 1,
        "description": "Synthetic three-peak demonstration only. Adjust all bounds/brackets for experimental data.",
        "initial_peaks": [{"peak_id": "cluster", "start_min": 5.6, "end_min": 8.1,
                           "start_mv": 0.115, "end_mv": 0.1775}],
        "operations": [
            {"op": "split_at_valley", "peak_id": "cluster", "between_min": [6.52, 6.75],
             "child_ids": ["region_1", "remainder"], "separation": "vertical"},
            {"op": "split_at_valley", "peak_id": "remainder", "between_min": [7.0, 7.25],
             "child_ids": ["region_2", "region_3"], "separation": "vertical"},
        ],
    }
    return time, signal, recipe
