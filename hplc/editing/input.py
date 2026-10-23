"""Load LCD or generic numeric CSV traces in minutes/mV."""
from pathlib import Path
import csv
import numpy as np
from . import PeakEditor
from ..lcd import read_chromatograms

CHANNELS = {"ri": (1, "RI_mV"), "uv210": (2, "UV_210nm_mV"), "uv254": (3, "UV_254nm_mV")}

def load_editor(source, channel="ri", time_column="time_min", signal_column=None):
    source = Path(source)
    if source.suffix.lower() == ".lcd":
        if signal_column is not None or time_column != "time_min":
            raise ValueError("CSV column options cannot be applied to LCD input.")
        number = CHANNELS[channel][0]
        record = next((c for c in read_chromatograms(source) if c["channel"] == number), None)
        if record is None or record["unit"] != "mV":
            raise ValueError("Requested mV detector trace is unavailable.")
        return PeakEditor(record["time"], record["signal"], f"{source.stem} | {record['label']}")
    if source.suffix.lower() != ".csv":
        raise ValueError("Input must be LCD or CSV.")
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        column = signal_column or (CHANNELS[channel][1] if CHANNELS[channel][1] in fields else "signal_mV")
        if time_column not in fields or column not in fields:
            raise ValueError(f"CSV needs {time_column} and {column}; specify --time-column/--signal-column if needed.")
        values = [(float(row[time_column]), float(row[column])) for row in reader]
    if len(values) < 2:
        raise ValueError("CSV needs at least two numeric data rows.")
    time, signal = np.asarray(values).T
    return PeakEditor(time, signal, f"{source.stem} | {column}")
