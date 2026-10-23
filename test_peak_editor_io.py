"""Focused peak editing regression tests."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from edit_peaks import apply_recipe, demo_trace_and_recipe, load_editor, run_file
from peak_editor import PeakEditor, trapezoids
from editor_test_helpers import PeakEditorCase

class PeakEditorTests(PeakEditorCase):
    def test_resume_audit_checks_trace_and_state(self):
        editor = self.editor()
        editor.insert_peak("all", 0, 4)
        editor.split_peak("all", 2)
        with tempfile.TemporaryDirectory() as directory:
            editor.export(directory)
            audit = Path(directory) / "edited_audit.json"
            resumed = PeakEditor.from_audit(editor.time_min, editor.signal_mv, audit)
            self.assertEqual(resumed.peak_table(), editor.peak_table())
            with self.assertRaises(ValueError):
                PeakEditor.from_audit(editor.time_min, editor.signal_mv + 1, audit)

    def test_export_headers_audit_and_csv_curve_integrals(self):
        editor = self.editor()
        editor.insert_peak("host", 0, 4, baseline="custom", knots=np.array([[0, 0], [4, 0]]))
        editor.skim_peak("host", "rider", 2, 4)
        with tempfile.TemporaryDirectory() as directory:
            path = editor.export(directory)
            with path.open(encoding="utf-8-sig") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 2)
            audit = json.loads((Path(directory) / "edited_audit.json").read_text())
            self.assertEqual(audit["area_unit"], "uV*s")
            self.assertEqual(len(audit["history"]), 2)
            with (Path(directory) / "edited_curves.csv").open(encoding="utf-8-sig") as handle:
                curves = list(csv.DictReader(handle))
            for row in rows:
                points = [p for p in curves if p["peak_id"] == row["peak_id"]]
                x = np.array([float(p["time_min"]) for p in points])
                y = np.array([float(p["allocated_mV"]) for p in points])
                self.assertAlmostEqual(trapezoids(x, y) * 60000, float(row["area_uV_s"]))

    def test_csv_recipe_end_to_end(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "two_peaks.csv"
            source.write_text("time_min,signal_mV\n0,0\n1,2\n2,1\n3,3\n4,0\n")
            recipe = {"initial_peaks": [{"peak_id": "all", "start_min": 0, "end_min": 4}],
                      "operations": [{"op": "split_at_valley", "peak_id": "all", "between_min": [1.5, 2.5], "child_ids": ["A", "B"]}]}
            editor, output = run_file(source, recipe, Path(directory) / "out")
            self.assertAlmostEqual(self.area(editor), 6)
            self.assertTrue(output.exists())
            self.assertTrue((output.parent / "two_peaks_ri_comparison.svg").exists())
            self.assertTrue((output.parent / "two_peaks_ri_comparison.png").exists())

    def test_recipe_rejects_unknown_operation(self):
        with self.assertRaises(ValueError):
            apply_recipe(self.editor(), {"operations": [{"op": "__getattribute__"}]})
        with self.assertRaises(ValueError):
            apply_recipe(self.editor(), {"unexpected": "value"})

    def test_three_peak_demo_and_area_conservation(self):
        x, y, recipe = demo_trace_and_recipe()
        editor = PeakEditor(x, y)
        before = apply_recipe(editor, recipe)
        self.assertEqual(len(editor.peak_table()), 3)
        original_area = sum(row["area_uV_s"] for row in editor.peak_table(state=before))
        edited_area = sum(row["area_uV_s"] for row in editor.peak_table())
        self.assertAlmostEqual(original_area, edited_area, places=7)
