"""Immutable peak definitions and numerical helpers."""
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class Peak:
    peak_id: str
    start_min: float
    end_min: float
    baseline_times: tuple
    baseline_values_mv: tuple
    method: str = "linear"
    enabled: bool = True
    parent_id: str = ""

def trapezoids(x, y):
    return float(np.sum(np.diff(x) * (y[:-1] + y[1:]) / 2))

def json_value(value):
    if isinstance(value, np.ndarray):
        return json_value(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value
