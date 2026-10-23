"""Peak editing: exporting."""
from dataclasses import asdict
import csv
import hashlib
import json
from pathlib import Path

class ExportOps:
    def export(self, output, prefix="edited", source=None):
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
        if Path(prefix).name != prefix or prefix in ("", ".", ".."):
            raise ValueError("Export prefix must be a simple nonempty file name.")
        fields = ["peak_id", "status", "parent_id", "method", "start_min", "end_min", "retention_time_min",
                  "height_uV", "area_uV_s", "area_mV_min", "envelope_area_uV_s", "skim_deduction_uV_s", "flags"]
        with (output / f"{prefix}_areas.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(self.peak_table())
        with (output / f"{prefix}_curves.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["peak_id", "time_min", "signal_mV", "baseline_mV", "allocated_mV"])
            for peak in self._peaks.values():
                if peak.enabled:
                    curve = self.curve(peak.peak_id)
                    writer.writerows((peak.peak_id, *row) for row in zip(curve["time_min"], curve["signal_mv"], curve["baseline_mv"], curve["allocated_mv"]))
        digest = hashlib.sha256(self.time_min.astype("<f8").tobytes() + self.signal_mv.astype("<f8").tobytes()).hexdigest()
        audit = {"schema_version": 1, "label": self.label, "source": str(source) if source else None,
                 "source_sha256": hashlib.sha256(Path(source).read_bytes()).hexdigest() if source else None,
                 "trace_sha256": digest, "signal_unit": "mV", "time_unit": "min", "area_unit": "uV*s",
                 "integration": "Signed trapezoids with interpolated exact bounds and all baseline knots; no smoothing or negative clipping.",
                 "overlap_note": "Vertical divisions and skims are user-defined allocations, not confirmed pure-component deconvolution or a reproduction of proprietary integration rules.",
                 "skim_note": "A host's allocated area subtracts all attached riders, including rejected riders. remove_skim reclaims an allocation.",
                 "peak_states": [asdict(p) for p in self._peaks.values()], "history": self.history}
        (output / f"{prefix}_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
        return output / f"{prefix}_areas.csv"
