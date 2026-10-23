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
    def test_failed_edit_is_atomic(self):
        editor = self.editor()
        editor.insert_peak("left", 0, 2)
        state, history = editor.snapshot(), editor.history
        with self.assertRaises(ValueError):
            editor.insert_peak("overlap", 1, 3)
        self.assertEqual(editor.snapshot(), state)
        self.assertEqual(editor.history, history)
        for knots in [[[0, 0], [0, 1]], [[1, 0], [3, 0]], [[-1, 0], [4, 0]]]:
            with self.subTest(knots=knots), self.assertRaises(ValueError):
                editor.set_baseline("left", "custom", knots=knots)
        self.assertEqual(editor.snapshot(), state)

    def test_reject_restore_undo_and_redo(self):
        editor = self.editor()
        editor.insert_peak("all", 0, 4)
        editor.reject_peak("all")
        self.assertEqual(editor.peak_table(), [])
        editor.undo()
        self.assertAlmostEqual(self.area(editor), 6)
        editor.redo()
        self.assertEqual(editor.peak_table(), [])
        editor.restore_peak("all")
        self.assertAlmostEqual(self.area(editor), 6)
        editor.undo()
        editor.restore_peak("all")
        with self.assertRaises(ValueError):
            editor.redo()

    def test_negative_areas_are_flagged_without_clipping(self):
        editor = self.editor()
        editor.insert_peak("all", 0, 4, start_mv=10, end_mv=10)
        row = editor.peak_table()[0]
        self.assertAlmostEqual(row["area_mV_min"], -34)
        self.assertIn("nonpositive_area", row["flags"])
        self.assertIn("baseline_crosses_signal", row["flags"])

    def test_history_replay_including_undo_and_valley_operation(self):
        editor = self.editor()
        editor.insert_peak("all", 0, 4)
        editor.split_at_valley("all", [1.5, 2.5], ["A", "B"])
        editor.reject_peak("A")
        editor.undo()
        editor.redo()
        replay = self.editor()
        for event in editor.history:
            replay.execute(event["operation"], **event["parameters"])
        self.assertEqual(editor.snapshot(), replay.snapshot())
        self.assertEqual(editor.peak_table(), replay.peak_table())
