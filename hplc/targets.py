"""Validated detector-specific target CSV configuration."""
import csv
import math

TARGET_FIELDS = ["target_name", "detector", "expected_rt_min", "tolerance_min", "min_area_uV_s"]
DETECTORS = {"RI", "UV_210nm", "UV_254nm"}
MATCH_FIELDS = ["filename", "target_name", "detector", "expected_rt_min", "tolerance_min",
                "min_area_uV_s", "min_retention_time_min", "status", "candidate_count",
                "peak_number", "retention_time_min", "rt_error_min", "area_uV_s", "height_uV",
                "start_min", "end_min", "note"]
PEAK_FIELDS = ["filename", "detector", "peak_number", "retention_time_min", "area_uV_s",
               "height_uV", "start_min", "end_min", "relative_area_percent", "passes_discovery_filter"]


def finite_number(value, name, minimum=0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a finite number.") from None
    if not math.isfinite(number) or number < minimum:
        raise ValueError(f"{name} must be finite and >= {minimum}.")
    return number

def load_targets(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not set(TARGET_FIELDS).issubset(reader.fieldnames):
            raise ValueError("Target CSV requires: " + ", ".join(TARGET_FIELDS))
        targets = []
        seen = set()
        for line, row in enumerate(reader, 2):
            target = {key: row[key].strip() if row[key] is not None else "" for key in TARGET_FIELDS}
            if not target["target_name"] or target["detector"] not in DETECTORS:
                raise ValueError(f"Target CSV line {line}: name required; detector must be RI, UV_210nm, or UV_254nm.")
            identity = target["target_name"], target["detector"]
            if identity in seen:
                raise ValueError(f"Duplicate target/detector on line {line}: {identity}")
            seen.add(identity)
            for key in TARGET_FIELDS[2:]:
                target[key] = finite_number(target[key], key)
            if target["tolerance_min"] == 0:
                raise ValueError("Retention tolerance must be > 0.")
            targets.append(target)
    if not targets:
        raise ValueError("Target CSV has no targets.")
    return targets
