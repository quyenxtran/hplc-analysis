"""Fit result with separate parameter, curve, provenance, and residual exports."""
from dataclasses import dataclass
from pathlib import Path
import csv
import json
from ..editing.model import json_value


@dataclass
class FitResult:
    metadata: dict
    curves: dict

    def to_dict(self):
        return json_value({**self.metadata, "curves": self.curves})

    def export(self, output, prefix="fitted"):
        if Path(prefix).name != prefix or prefix in ("", ".", ".."):
            raise ValueError("Fit prefix must be a simple file name.")
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
        rows = self.metadata["components"]
        with (output / f"{prefix}_components.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        with (output / f"{prefix}_fit_curves.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(self.curves)
            writer.writerows(zip(*self.curves.values()))
        path = output / f"{prefix}_fit.json"
        path.write_text(json.dumps(json_value(self.metadata), indent=2, allow_nan=False), encoding="utf-8")
        from .plotting import plot_fit
        plot_fit(self, output / f"{prefix}_fit.svg")
        return path
