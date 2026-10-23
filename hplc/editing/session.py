"""Restore an editing session by verifying and replaying its audit trail."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from .model import json_value


class SessionOps:
    @classmethod
    def from_audit(cls, time_min, signal_mv, audit):
        if isinstance(audit, (str, Path)):
            audit = json.loads(Path(audit).read_text(encoding="utf-8-sig"))
        if not isinstance(audit, dict) or audit.get("schema_version") != 1:
            raise ValueError("Unsupported editing audit schema.")
        if audit.get("signal_unit") != "mV" or audit.get("time_unit") != "min":
            raise ValueError("Audit must use mV and minutes.")
        editor = cls(time_min, signal_mv, audit.get("label", "Chromatogram"))
        raw = editor.time_min.astype("<f8").tobytes() + editor.signal_mv.astype("<f8").tobytes()
        if hashlib.sha256(raw).hexdigest() != audit.get("trace_sha256"):
            raise ValueError("Trace hash differs from audit; refusing to replay edits on different data.")
        for event in audit.get("history", []):
            editor.execute(event["operation"], **event["parameters"])
        actual = json_value([asdict(p) for p in editor.peaks.values()])
        if actual != audit.get("peak_states"):
            raise ValueError("Replayed state differs from recorded state; review audit/version.")
        return editor
