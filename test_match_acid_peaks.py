"""Target matching checks with synthetic acid mixtures and folder fixtures."""
import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from match_acid_peaks import discover_peaks, export_folder, load_targets, match_targets


def peak(number, time, area=5000):
    return {"peak_number": number, "retention_time_min": time, "area_uV_s": area,
            "height_uV": 500, "start_min": time - 0.2, "end_min": time + 0.4}


def channel(key, peaks):
    return {"key": key, "peaks": peaks, "status": "ok" if peaks else "no_saved_peaks"}


def target(name="acid_A", detector="RI", time=7, tolerance=0.1, minimum=1000):
    return {"target_name": name, "detector": detector, "expected_rt_min": time,
            "tolerance_min": tolerance, "min_area_uV_s": minimum}


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

    def test_discovery_has_no_fixed_upper_bound(self):
        rows = discover_peaks([channel("RI", [peak(1, 4.99, 1e9), peak(2, 5), peak(3, 20, 1500)])])
        self.assertEqual([r["retention_time_min"] for r in rows], [5, 20])
        self.assertTrue(all(r["passes_discovery_filter"] for r in rows))

    def test_target_config_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "targets.csv"
            path.write_text("target_name,detector,expected_rt_min,tolerance_min,min_area_uV_s\nacid_A,RI,7,0.1,1000\n")
            self.assertEqual(load_targets(path)[0]["expected_rt_min"], 7)
            with path.open("a") as handle:
                handle.write("acid_A,RI,8,0.1,1000\n")
            with self.assertRaises(ValueError):
                load_targets(path)
            path.write_text("target_name,detector,expected_rt_min,tolerance_min,min_area_uV_s\nacid_A,RI,nan,0.1,1000\n")
            with self.assertRaises(ValueError):
                load_targets(path)

    def test_folder_coverage_exclusions_and_file_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for name in ["sample1.lcd", "sample2.lcd", "wait.lcd"]:
                (folder / name).write_bytes(b"fixture")
            with patch("match_acid_peaks.read_saved_peaks", side_effect=[
                    [channel("RI", [peak(1, 7)])], ValueError("bad file")]):
                rows, _, metadata = export_folder(folder, folder / "out", [target()], excludes=["wait.lcd"])
            self.assertEqual(len(metadata["files"]), 2)
            self.assertEqual([r["status"] for r in rows], ["matched", "file_error"])
            with (folder / "out/target_matches.csv").open(encoding="utf-8-sig") as handle:
                csv_rows = list(csv.DictReader(handle))
            self.assertEqual(len(csv_rows), 2)
            self.assertEqual(csv_rows[1]["area_uV_s"], "")


if __name__ == "__main__":
    unittest.main()
