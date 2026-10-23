"""Shared synthetic trace fixtures for editor tests."""
import unittest
from peak_editor import PeakEditor

class PeakEditorCase(unittest.TestCase):
    def editor(self):
        return PeakEditor([0, 1, 2, 3, 4], [0, 2, 1, 3, 0])

    def area(self, editor, peak_id=None):
        rows = editor.peak_table()
        return sum(row["area_mV_min"] for row in rows if peak_id is None or row["peak_id"] == peak_id)
