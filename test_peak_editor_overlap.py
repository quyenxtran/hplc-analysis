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
    def test_baseline_separation_and_vertical_switch(self):
        editor = self.editor()
        editor.insert_peak("all", 0, 4)
        editor.split_peak("all", 2, ["left", "right"], separation="baseline")
        self.assertAlmostEqual(self.area(editor), 4)
        editor.set_separation("left", "right", "vertical")
        self.assertAlmostEqual(self.area(editor), 6)
        editor.set_separation("left", "right", "baseline")
        self.assertAlmostEqual(self.area(editor), 4)

    def test_valley_search_requires_local_minimum(self):
        editor = self.editor()
        editor.insert_peak("all", 0, 4)
        self.assertEqual(editor.find_valley("all", [1.5, 2.5]), 2)
        editor.split_at_valley("all", [1.5, 2.5], ["left", "right"])
        self.assertAlmostEqual(self.area(editor), 6)
        monotone = PeakEditor(np.linspace(0, 4, 41), np.linspace(0, 4, 41))
        monotone.insert_peak("all", 0, 4, baseline="zero")
        with self.assertRaises(ValueError):
            monotone.find_valley("all", [1, 3])

    def test_skim_conserves_total_and_exports_allocated_curve(self):
        editor = self.editor()
        editor.insert_peak("host", 0, 4)
        editor.skim_peak("host", "rider", 2, 4)
        self.assertAlmostEqual(self.area(editor, "rider"), 2.5)
        self.assertAlmostEqual(self.area(editor, "host"), 3.5)
        self.assertAlmostEqual(self.area(editor), 6)
        for row in editor.peak_table():
            curve = editor.curve(row["peak_id"])
            self.assertAlmostEqual(trapezoids(curve["time_min"], curve["allocated_mv"]), row["area_mV_min"])

    def test_discontinuous_skim_anchors_do_not_lose_boundary_area(self):
        editor = self.editor()
        editor.insert_peak("host", 0, 4)
        editor.skim_peak("host", "rider", 2, 4, start_mv=0.5, end_mv=0.2)
        self.assertAlmostEqual(self.area(editor, "rider"), 2.8)
        self.assertAlmostEqual(self.area(editor, "host"), 3.2)
        self.assertAlmostEqual(self.area(editor), 6)

    def test_reject_skim_excludes_it_without_reassigning_to_host(self):
        editor = self.editor()
        editor.insert_peak("host", 0, 4)
        editor.skim_peak("host", "rider", 2, 4)
        editor.reject_peak("rider")
        self.assertAlmostEqual(self.area(editor), 3.5)
        editor.remove_skim("rider")
        self.assertAlmostEqual(self.area(editor), 6)

    def test_skim_overlap_and_nesting_are_rejected(self):
        editor = self.editor()
        editor.insert_peak("host", 0, 4)
        editor.skim_peak("host", "rider", 2, 4)
        for operation in [lambda: editor.skim_peak("host", "bad", 1, 3),
                          lambda: editor.skim_peak("rider", "bad", 2.5, 3.5),
                          lambda: editor.split_peak("host", 1)]:
            with self.assertRaises(ValueError):
                operation()
        editor.reject_peak("host")
        self.assertEqual(editor.peak_table(), [])

    def test_unify_does_not_swallow_unselected_peak(self):
        editor = self.editor()
        for name, start, end in [("A", 0, 1), ("B", 1, 2), ("C", 2, 4)]:
            editor.insert_peak(name, start, end)
        with self.assertRaises(ValueError):
            editor.unify_peaks(["A", "C"], "bad")
