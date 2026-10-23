"""Focused acid-matcher regression tests."""
import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from match_acid_peaks import discover_peaks, export_folder, load_targets, match_targets
from acid_test_helpers import peak, channel, target

class TargetMatchingTests(unittest.TestCase):
    def test_detector_specific_times_and_larger_interferent(self):
        channels = [channel("RI", [peak(1, 6.2, 1e8), peak(2, 7.02, 4000)]),
                    channel("UV_210nm", [peak(1, 6.88, 3000)])]
        rows, _ = match_targets(channels, [target(), target(detector="UV_210nm", time=6.88)])
        self.assertEqual([r["status"] for r in rows], ["matched", "matched"])
        self.assertEqual(rows[0]["peak_number"], 2)
        self.assertEqual(rows[0]["area_uV_s"], 4000)

    def test_weak_acid_not_rejected_relative_to_strong_acid(self):
        rows, _ = match_targets([channel("RI", [peak(1, 6, 1e9), peak(2, 8, 1500)])],
                                [target(time=6), target(name="acid_B", time=8)])
        self.assertTrue(all(row["status"] == "matched" for row in rows))
        self.assertEqual(rows[1]["area_uV_s"], 1500)

    def test_ambiguity_leaves_area_blank(self):
        rows, candidates = match_targets([channel("RI", [peak(1, 6.99), peak(2, 7.01, 1e7)])], [target()])
        self.assertEqual(rows[0]["status"], "ambiguous_multiple_peaks")
        self.assertEqual(rows[0]["candidate_count"], 2)
        self.assertEqual(rows[0]["area_uV_s"], "")
        self.assertEqual(len(candidates), 2)

    def test_shared_peak_cannot_be_assigned_to_two_acids(self):
        rows, _ = match_targets([channel("RI", [peak(1, 7)])],
                                [target(), target(name="acid_B", time=7.01)])
        self.assertTrue(all(row["status"] == "assignment_conflict" for row in rows))
        self.assertTrue(all(row["area_uV_s"] == "" for row in rows))

    def test_missing_and_low_area_and_cutoff(self):
        rows, _ = match_targets([channel("RI", [peak(1, 7, 999)])],
                                [target(), target(name="acid_B", time=9), target(detector="UV_254nm"),
                                 target(name="early", time=4.9)])
        self.assertEqual([r["status"] for r in rows],
                         ["below_min_area", "not_detected", "missing_detector", "target_below_retention_cutoff"])
        self.assertTrue(all(row["area_uV_s"] == "" for row in rows))

    def test_unique_match_shared_with_ambiguous_target_is_flagged(self):
        rows, _ = match_targets([channel("RI", [peak(1, 7), peak(2, 7.15)])],
                                [target(tolerance=0.2), target(name="acid_B", tolerance=0.05)])
        self.assertEqual(rows[0]["status"], "ambiguous_multiple_peaks")
        self.assertEqual(rows[1]["status"], "assignment_conflict")
        self.assertTrue(all(row["area_uV_s"] == "" for row in rows))

    def test_tolerance_boundary_and_no_matching_outside(self):
        rows, _ = match_targets([channel("RI", [peak(1, 7.1)])], [target()])
        self.assertEqual(rows[0]["status"], "matched")
        rows, _ = match_targets([channel("RI", [peak(1, 7.1001)])], [target()])
        self.assertEqual(rows[0]["status"], "not_detected")
