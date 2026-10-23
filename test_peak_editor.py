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
    def test_validates_trace_and_keeps_raw_unchanged(self):
        for x, y in [([0, 0], [1, 2]), ([0, 1], [1, np.nan]), ([0, 1], [1]), ([[0, 1]], [[1, 2]])]:
            with self.subTest(x=x), self.assertRaises(ValueError):
                PeakEditor(x, y)
        x, y = np.arange(5, dtype=float), np.array([0, 2, 1, 3, 0.0])
        editor = PeakEditor(x, y)
        editor.insert_peak("all", 0, 4)
        editor.split_peak("all", 2)
        np.testing.assert_array_equal(editor.signal_mv, y)
        y[1] = 100
        self.assertEqual(editor.signal_mv[1], 2)
        with self.assertRaises(ValueError):
            editor.signal_mv[1] = 10

    def test_known_area_and_uv_seconds_conversion(self):
        editor = self.editor()
        editor.insert_peak("all", 0, 4)
        self.assertAlmostEqual(self.area(editor), 6)
        self.assertAlmostEqual(editor.peak_table()[0]["area_uV_s"], 360000)

    def test_non_grid_split_conserves_area(self):
        editor = self.editor()
        editor.insert_peak("all", 0.25, 3.75, baseline="zero")
        initial = self.area(editor)
        editor.split_n_peaks("all", [1.3, 2.65], ["A", "B", "C"])
        self.assertAlmostEqual(self.area(editor), initial, places=12)
        editor.unify_peaks(["A", "B", "C"], "merged", baseline="preserve")
        self.assertAlmostEqual(self.area(editor), initial, places=12)

    def test_custom_baseline_knots_are_integrated_exactly(self):
        editor = PeakEditor([0, 2, 4], [10, 10, 10])
        editor.insert_peak("all", 0, 4, baseline="custom", knots=np.array([[0, 0], [1, 2], [4, 0]]))
        self.assertAlmostEqual(self.area(editor), 36)
        editor.split_n_peaks("all", [0.7, 2.3])
        self.assertAlmostEqual(self.area(editor), 36)

    def test_move_time_and_intensity_endpoints(self):
        editor = PeakEditor([0, 1, 2, 3, 4], [2, 3, 4, 5, 6])
        editor.insert_peak("all", 0, 4, baseline="zero")
        self.assertAlmostEqual(self.area(editor), 16)
        editor.move_baseline("all", start_min=1, end_min=3)
        self.assertEqual(editor.peaks["all"].baseline_values_mv, (3, 5))
        self.assertAlmostEqual(self.area(editor), 0)
        editor.move_baseline("all", start_mv=0, end_mv=0)
        self.assertAlmostEqual(self.area(editor), 8)

    def test_horizontal_and_zero_baselines(self):
        editor = self.editor()
        editor.insert_peak("all", 0, 4)
        editor.set_baseline("all", mode="horizontal", start_mv=0.5)
        self.assertAlmostEqual(self.area(editor), 4)
        editor.set_baseline("all", mode="zero")
        self.assertAlmostEqual(self.area(editor), 6)
