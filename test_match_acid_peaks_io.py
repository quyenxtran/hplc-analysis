"""Focused acid-matcher regression tests."""
import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from match_acid_peaks import discover_peaks, export_folder, load_targets, match_targets
from acid_test_helpers import peak, channel, target

class TargetMatchingTests(unittest.TestCase):
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
            with patch("hplc.target_export.read_saved_peaks", side_effect=[
                    [channel("RI", [peak(1, 7)])], ValueError("bad file")]):
                rows, _, metadata = export_folder(folder, folder / "out", [target()], excludes=["wait.lcd"])
            self.assertEqual(len(metadata["files"]), 2)
            self.assertEqual([r["status"] for r in rows], ["matched", "file_error"])
            with (folder / "out/target_matches.csv").open(encoding="utf-8-sig") as handle:
                csv_rows = list(csv.DictReader(handle))
            self.assertEqual(len(csv_rows), 2)
            self.assertEqual(csv_rows[1]["area_uV_s"], "")
