"""Workbench state transitions, stale-fit invalidation, and audit round trips."""
import json
from pathlib import Path
import tempfile
import unittest
from hplc.workbench.state import Workbench


class WorkbenchTests(unittest.TestCase):
    def call(self, workbench, action, **kwargs):
        return workbench.dispatch({"revision": workbench.revision, "action": action, **kwargs})

    def test_fit_edit_undo_export_and_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            w = Workbench(output=directory)
            self.call(w, "fit", parameters={"peak_id": "envelope", "centers_min": [6.8, 7.08, 7.36], "starts": 1})
            self.assertEqual(len(w.payload()["fit"]["components"]), 3)
            self.call(w, "export")
            self.assertEqual(len(list(Path(directory).glob("*_fit.json"))), 1)
            self.call(w, "edit", op="move_baseline", parameters={"peak_id": "envelope", "start_mv": .09})
            self.assertIsNone(w.payload()["fit"])
            self.call(w, "edit", op="undo")
            self.assertIsNone(w.fit)
            self.call(w, "export")
            audits = sorted(Path(directory).glob("*_audit.json"))
            data = json.loads(audits[-1].read_text())
            restored = Workbench()
            self.call(restored, "restore", audit=data)
            self.assertEqual(restored.editor.snapshot(), w.editor.snapshot())

    def test_stale_revision_and_invalid_edit_do_not_mutate_state(self):
        w = Workbench()
        state = w.editor.snapshot()
        with self.assertRaisesRegex(ValueError, "Session changed"):
            w.dispatch({"revision": -1, "action": "edit", "op": "undo"})
        with self.assertRaises(ValueError):
            self.call(w, "edit", op="move_baseline", parameters={"peak_id": "envelope", "start_min": 9})
        self.assertEqual(w.editor.snapshot(), state)
        self.assertEqual(w.revision, 0)

    def test_folder_file_and_channel_load(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for name in ["a.csv", "b.csv"]:
                (folder / name).write_text("time_min,RI_mV,UV_210nm_mV\n0,0,1\n1,2,3\n2,0,1\n")
            w = Workbench(folder)
            self.assertEqual(w.payload()["files"], ["a.csv", "b.csv"])
            self.call(w, "load", index=1, channel="uv210")
            self.assertEqual(w.editor.signal_mv.tolist(), [1, 3, 1])
            self.assertEqual(w.payload()["source_index"], 1)
            self.assertEqual(w.editor.peaks, {})


if __name__ == "__main__":
    unittest.main()
