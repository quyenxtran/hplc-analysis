"""One in-memory editing session, guarded by a server-side revision counter."""
import time
from pathlib import Path
import numpy as np
from ..editing import PeakEditor
from ..editing.input import load_editor
from ..fitting.demo import fitting_demo
from ..sorting import natural_key


class Workbench:
    def __init__(self, source=None, channel="ri", output="editing_results/workbench"):
        self.files = []
        if source:
            source = Path(source)
            self.files = sorted((p for p in source.iterdir() if p.is_file() and p.suffix.lower() in (".lcd", ".csv")), key=lambda p: natural_key(p.name)) if source.is_dir() else [source]
            if not self.files:
                raise ValueError("No LCD or CSV files found.")
        self.channel, self.output, self.revision = channel, Path(output), 0
        self.source, self.fit = None, None
        self.editor = fitting_demo()[0]
        if self.files:
            self.load(0, channel)

    def load(self, index, channel):
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(self.files):
            raise ValueError("Choose a valid input file.")
        editor = load_editor(self.files[index], channel)
        self.editor, self.source, self.channel = editor, self.files[index], channel
        self.fit = None

    def payload(self):
        e = self.editor
        peaks = []
        for p in e.peaks.values():
            peaks.append({"peak_id": p.peak_id, "start_min": p.start_min, "end_min": p.end_min,
                          "enabled": p.enabled, "parent_id": p.parent_id,
                          "baseline_times": p.baseline_times, "baseline_values_mv": p.baseline_values_mv,
                          "endpoints_mv": np.interp([p.start_min, p.end_min], p.baseline_times, p.baseline_values_mv).tolist()})
        return {"revision": self.revision, "label": e.label, "channel": self.channel,
                "files": [p.name for p in self.files], "source_index": self.files.index(self.source) if self.source in self.files else -1,
                "time": e.time_min.tolist(), "signal": e.signal_mv.tolist(), "peaks": peaks,
                "rows": e.peak_table(include_rejected=True), "undo": bool(e._undo), "redo": bool(e._redo),
                "fit": self.fit.to_dict() if self.fit else None}

    def dispatch(self, data):
        if data.get("revision") != self.revision:
            raise ValueError("Session changed; refresh before applying another action.")
        action = data.get("action")
        message = "Updated"
        if action == "edit":
            self.editor.execute(data["op"], **data.get("parameters", {}))
            self.fit = None
        elif action == "fit":
            self.fit = None
            self.fit = self.editor.fit_components(**data["parameters"])
        elif action == "load":
            self.load(data["index"], data.get("channel", self.channel))
        elif action == "restore":
            editor = PeakEditor.from_audit(self.editor.time_min, self.editor.signal_mv, data["audit"])
            self.editor, self.fit = editor, None
        elif action == "export":
            prefix = f"session_{time.time_ns()}"
            path = self.editor.export(self.output, prefix, self.source)
            if self.fit:
                self.fit.export(self.output, prefix)
            message = "Saved: " + str(path.resolve())
        else:
            raise ValueError("Unknown workbench action.")
        self.revision += 1
        return {"message": message, "state": self.payload()}
