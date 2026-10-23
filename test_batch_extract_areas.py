"""Tests for exact vendor peak-table export and summary selection."""
import struct
import unittest

from batch_extract_areas import parse_peak_table, read_saved_peaks, select_main_peak, natural_key, filter_peaks
from plot_hplc import DEFAULT_SOURCE


class SavedPeakTests(unittest.TestCase):
    def test_absolute_and_relative_area_filter(self):
        peaks = [{"retention_time_min": t, "area_uV_s": a} for t, a in
                 [(2, 1e9), (7, 200000), (8, 2000), (9, 1999), (10, 999), (11, -3000)]]
        kept, threshold, reference = filter_peaks(peaks, 6, 12, 1000, 1)
        self.assertEqual(reference, 200000)  # Outside-window peak does not set reference.
        self.assertEqual(threshold, 2000)
        self.assertEqual([p["area_uV_s"] for p in kept], [200000, 2000])
        self.assertEqual(len(peaks), 6)  # Filtering does not mutate original records.
        kept, threshold, _ = filter_peaks(peaks, 6, 12, 1000, 0)
        self.assertEqual(threshold, 1000)
        self.assertEqual(len(kept), 3)

    def test_empty_or_fully_rejected_peak_list(self):
        self.assertEqual(filter_peaks([], 6, 12), ([], 1000, 0))
        self.assertEqual(select_main_peak([{"retention_time_min": 7, "area_uV_s": 999}], 6, 12, 1000), (None, 0))

    def test_invalid_thresholds(self):
        for minimum, relative in [(-1, 1), (float("nan"), 1), (1000, -1), (1000, 101), (1000, float("inf"))]:
            with self.subTest(minimum=minimum, relative=relative), self.assertRaises(ValueError):
                filter_peaks([], 6, 12, minimum, relative)

    def test_vendor_record_precision_and_times(self):
        raw = bytearray(20 + 792)
        raw[:4] = b"VER1"
        struct.pack_into("<I", raw, 4, 1)
        struct.pack_into("<I", raw, 24, 420000)
        struct.pack_into("<d", raw, 28, 303175.4341632128)
        struct.pack_into("<d", raw, 44, 11149.26023667721)
        struct.pack_into("<2I", raw, 76, 390000, 540000)
        peak = parse_peak_table(raw)[0]
        self.assertEqual(peak["area_uV_s"], 303175.4341632128)
        self.assertEqual(peak["retention_time_min"], 7)
        self.assertEqual(peak["start_min"], 6.5)
        self.assertEqual(peak["end_min"], 9)

    def test_empty_and_padded_empty_tables(self):
        for size in [20, 812]:
            raw = bytearray(size)
            raw[:4] = b"VER1"
            self.assertEqual(parse_peak_table(raw), [])

    def test_reject_corrupt_table(self):
        with self.assertRaises(ValueError):
            parse_peak_table(b"invalid")
        raw = bytearray(22)
        raw[:4] = b"VER1"
        struct.pack_into("<I", raw, 4, 2)
        with self.assertRaises(ValueError):
            parse_peak_table(raw)

    def test_selection_preserves_all_peaks(self):
        peaks = [{"retention_time_min": t, "area_uV_s": a} for t, a in [(2, 1e6), (7, 30), (8, 10), (9, -1)]]
        main, count = select_main_peak(peaks, 6, 12)
        self.assertEqual(main["area_uV_s"], 30)
        self.assertEqual(count, 2)
        self.assertEqual(len(peaks), 4)
        self.assertEqual(select_main_peak(peaks, 10, 12), (None, 0))

    def test_natural_order(self):
        self.assertEqual(sorted(["47A1_10.lcd", "47A1_2.lcd", "47A1_1.lcd"], key=natural_key),
                         ["47A1_1.lcd", "47A1_2.lcd", "47A1_10.lcd"])

    @unittest.skipUnless(DEFAULT_SOURCE.exists(), "Original LCD not present")
    def test_matches_shimadzu_screenshot(self):
        channels = read_saved_peaks(DEFAULT_SOURCE)
        ri = next(c for c in channels if c["key"] == "RI")
        self.assertEqual(len(ri["peaks"]), 1)
        peak = ri["peaks"][0]
        self.assertEqual(round(peak["area_uV_s"]), 303175)
        self.assertEqual(round(peak["height_uV"]), 11149)
        self.assertEqual(round(peak["retention_time_min"], 3), 7.146)


if __name__ == "__main__":
    unittest.main()
