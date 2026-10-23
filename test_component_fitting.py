"""Numerical recovery tests using independently generated positive mixtures."""
import unittest
import numpy as np
from scipy.stats import exponnorm
from peak_editor import PeakEditor
from hplc.fitting.demo import fitting_demo


class FittingTests(unittest.TestCase):
    def test_three_overlapping_gaussians_recover_known_areas_without_editing(self):
        editor, truth = fitting_demo()
        before, history = editor.snapshot(), editor.history
        result = editor.fit_components("envelope", [6.79, 7.09, 7.35], starts=3)
        rows = result.metadata["components"]
        np.testing.assert_allclose([r["area_full_model_uV_s"] for r in rows], truth[:, 0] * 60000, rtol=1e-6)
        np.testing.assert_allclose([r["location_min"] for r in rows], truth[:, 1], atol=1e-6)
        self.assertLess(result.metadata["diagnostics"]["rmse_mv"], 1e-8)
        d = result.metadata["diagnostics"]
        self.assertAlmostEqual(d["measured_window_area_uV_s"] - d["fitted_window_area_uV_s"], d["residual_area_uV_s"])
        self.assertEqual(editor.snapshot(), before)
        self.assertEqual(editor.history, history)
        self.assertFalse(editor.signal_mv.flags.writeable)

    def test_tailing_emg_areas_and_locations(self):
        x = np.linspace(5, 9, 801)
        y = .1 + .6 * exponnorm.pdf(x, 2, loc=6.5, scale=.09)
        y += .8 * exponnorm.pdf(x, 1.5, loc=6.95, scale=.12)
        editor = PeakEditor(x, y)
        editor.insert_peak("p", 5.5, 8.8, start_mv=.1, end_mv=.1)
        fit = editor.fit_components("p", [6.49, 6.96], model="emg", starts=3)
        rows = fit.metadata["components"]
        np.testing.assert_allclose([r["area_full_model_uV_s"] for r in rows], [36000, 48000], rtol=1e-5)
        np.testing.assert_allclose([r["tau_min"] for r in rows], [.18, .18], rtol=1e-5)
        self.assertTrue(all(r["apex_min"] > r["location_min"] for r in rows))

    def test_window_area_is_distinct_from_extrapolated_full_area(self):
        x = np.linspace(0, 2, 501)
        y = np.exp(-.5 * ((x - 1) / .3) ** 2)
        editor = PeakEditor(x, y)
        editor.insert_peak("p", .7, 1.3, baseline="zero")
        fit = editor.fit_components("p", [1], starts=1)
        row = fit.metadata["components"][0]
        self.assertAlmostEqual(row["fraction_in_window"], .682689492, places=6)
        self.assertLess(row["area_window_uV_s"], row["area_full_model_uV_s"])
        self.assertIn("truncated_components", fit.metadata["diagnostics"]["flags"])

    def test_invalid_configuration_and_skimmed_envelope_fail(self):
        editor, _ = fitting_demo()
        for params in ({"centers_min": []}, {"centers_min": [7, 6.8]},
                       {"centers_min": [6.8, 6.8]}, {"centers_min": [float("nan")]},
                       {"centers_min": [6.8], "model": "unknown"},
                       {"centers_min": [6.8], "starts": 0},
                       {"centers_min": [6.8], "center_tolerance_min": -1}):
            with self.subTest(params=params), self.assertRaises(ValueError):
                editor.fit_components("envelope", **params)
        editor.skim_peak("envelope", "rider", 7.1, 7.6)
        with self.assertRaisesRegex(ValueError, "skim"):
            editor.fit_components("envelope", [6.8, 7.1])

    def test_flat_negative_and_sparse_data_are_rejected(self):
        for x, y in ((np.linspace(0, 2, 20), np.zeros(20)),
                     (np.linspace(0, 2, 20), -np.ones(20)),
                     (np.linspace(0, 2, 4), np.ones(4))):
            editor = PeakEditor(x, y)
            editor.insert_peak("p", 0, 2, baseline="zero")
            with self.assertRaises(ValueError):
                editor.fit_components("p", [1], starts=1)


if __name__ == "__main__":
    unittest.main()
