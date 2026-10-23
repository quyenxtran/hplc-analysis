"""Numerical checks for peak integration. Run: python -m unittest discover -s hplc_plots/47A0"""
import unittest
import json
import numpy as np
from integrate_peak import integrate_window, load_channels, area_to_uv_seconds
from plot_hplc import DEFAULT_SOURCE
from pathlib import Path


class IntegrationTests(unittest.TestCase):
    def test_shimadzu_area_units_match_direct_integration(self):
        time_min = np.array([0, 1, 2], dtype=float)
        signal_mv = np.array([0, 2, 0], dtype=float)
        result = integrate_window(time_min, signal_mv, 0, 2)
        converted = area_to_uv_seconds(result["net_area"])
        # Independently integrate uV against seconds to catch either missing factor.
        time_s, signal_uv = time_min * 60, signal_mv * 1000
        direct = np.sum(np.diff(time_s) * (signal_uv[:-1] + signal_uv[1:]) / 2)
        self.assertEqual(converted, 120_000)
        self.assertEqual(converted, direct)
        self.assertEqual(area_to_uv_seconds(-2), -120_000)

    def test_triangle_on_sloping_baseline(self):
        time = np.array([0, 1, 2, 3, 4], dtype=float)
        signal = 5 + 2 * time + np.array([0, 2, 4, 2, 0])
        result = integrate_window(time, signal, 0, 4)
        self.assertAlmostEqual(result["net_area"], 8)
        self.assertAlmostEqual(result["baseline_area"], 36)
        self.assertAlmostEqual(result["raw_area"], 44)
        self.assertEqual(result["apex_time_min"], 2)

    def test_off_grid_bounds(self):
        result = integrate_window([0, 1, 2], [0, 2, 0], 0.25, 1.75)
        self.assertAlmostEqual(result["raw_area"], 1.875)
        self.assertAlmostEqual(result["baseline_area"], 0.75)
        self.assertAlmostEqual(result["net_area"], 1.125)
        np.testing.assert_allclose(result["time"], [0.25, 1, 1.75])

    def test_negative_signal_is_not_clipped(self):
        result = integrate_window([0, 1, 2], [0, -2, 0], 0, 2)
        self.assertAlmostEqual(result["net_area"], -2)

    def test_zero_baseline_and_irregular_sampling(self):
        result = integrate_window([0, 0.2, 1, 2], [1, 1.4, 3, 5], 0.1, 1.5, "none")
        self.assertAlmostEqual(result["net_area"], (1.5 + 1.5 ** 2) - (0.1 + 0.1 ** 2))
        self.assertEqual(result["baseline_area"], 0)

    def test_invalid_inputs(self):
        cases = [([0, 0, 1], [1, 2, 3], 0, 1), ([0, 1], [1, np.nan], 0, 1),
                 ([0, 1], [1, 2], -0.1, 1), ([0, 1], [1, 2], 1, 0),
                 ([0, 1], [1, 2], 0, 2), ([0, 1], [1, 2], 0, float("nan"))]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                integrate_window(*args)

    def test_saved_csv_matches_original_calibration(self):
        folder = Path(__file__).parent
        data = np.genfromtxt(folder / "47A0_chromatograms.csv", delimiter=",", names=True)
        metadata = json.loads((folder / "47A0_metadata.json").read_text())
        for channel, name in zip(metadata["channels"], ["RI", "UV_210nm", "UV_254nm"]):
            expected = data[name + "_raw_counts"] * channel["calibration_factor"] / channel["value_factor"]
            np.testing.assert_allclose(data[name + "_mV"], expected, rtol=1e-10, atol=1e-10)
            self.assertEqual(len(expected), channel["points"])

    @unittest.skipUnless(DEFAULT_SOURCE.exists(), "Original LCD not present")
    def test_lcd_and_exported_csv_agree(self):
        lcd = load_channels(DEFAULT_SOURCE)
        csv = load_channels(Path(__file__).parent / "47A0_chromatograms.csv")
        for a, b in zip(lcd, csv):
            ra = integrate_window(a["time"], a["signal"], 6, 12)
            rb = integrate_window(b["time"], b["signal"], 6, 12)
            self.assertAlmostEqual(ra["net_area"], rb["net_area"], places=6)
            self.assertAlmostEqual(ra["raw_area"], ra["net_area"] + ra["baseline_area"], places=8)


if __name__ == "__main__":
    unittest.main()
