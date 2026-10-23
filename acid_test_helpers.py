"""Synthetic peaks and target configurations for matcher tests."""
def peak(number, time, area=5000):
    return {"peak_number": number, "retention_time_min": time, "area_uV_s": area,
            "height_uV": 500, "start_min": time - 0.2, "end_min": time + 0.4}

def channel(key, peaks):
    return {"key": key, "peaks": peaks, "status": "ok" if peaks else "no_saved_peaks"}

def target(name="acid_A", detector="RI", time=7, tolerance=0.1, minimum=1000):
    return {"target_name": name, "detector": detector, "expected_rt_min": time,
            "tolerance_min": tolerance, "min_area_uV_s": minimum}
