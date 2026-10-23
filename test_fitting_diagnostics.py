"""Ambiguous fits, irregular sampling, deterministic starts, and durable outputs."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from peak_editor import PeakEditor
from hplc.fitting.demo import fitting_demo


class FitDiagnosticTests(unittest.TestCase):
    def test_noisy_three_component_ambiguity_is_reported(self):
        clean, truth = fitting_demo()
        y = clean.signal_mv + np.random.default_rng(9).normal(0, .01, len(clean.time_min))
        editor = PeakEditor(clean.time_min, y)
        editor.insert_peak("p", 5.8, 8.3, start_mv=.086, end_mv=.136)
        result = editor.fit_components("p", [6.79, 7.07, 7.37], starts=5)
        area = sum(r["area_full_model_uV_s"] for r in result.metadata["components"])
        self.assertAlmostEqual(area / (truth[:, 0].sum() * 60000), 1, places=3)
        flags = set(result.metadata["diagnostics"]["flags"])
        self.assertTrue(flags & {"alternative_area_solutions", "large_conditional_area_uncertainty", "weak_identifiability"})
        if "alternative_area_solutions" in flags:
            self.assertTrue(all(r["area_full_model_se_uV_s"] is None for r in result.metadata["components"]))
        self.assertLess(result.metadata["diagnostics"]["rmse_mv"], .012)

    def test_unresolved_two_components_flagged_instead_of_claimed_unique(self):
        x = np.linspace(0, 2, 301)
        y = np.exp(-.5 * ((x - 1) / .2) ** 2)
        editor = PeakEditor(x, y)
        editor.insert_peak("p", 0, 2, baseline="zero")
        try:
            fit = editor.fit_components("p", [.99, 1.01], starts=3)
        except ValueError as error:
            self.assertIn("did not converge", str(error))
            self.assertEqual(list(editor.peaks), ["p"])
            return
        flags = fit.metadata["diagnostics"]["flags"]
        self.assertTrue(set(flags) & {"weak_identifiability", "high_component_overlap", "alternative_area_solutions", "parameter_at_bound"})
        self.assertTrue(all(r["area_full_model_se_uV_s"] is None for r in fit.metadata["components"]))

    def test_singular_component_jacobian_suppresses_uncertainty(self):
        from types import SimpleNamespace
        from hplc.fitting.diagnostics import diagnostics
        curves = np.vstack([np.linspace(0, 1, 30)] * 2)
        best = SimpleNamespace(jac=np.ones((30, 6)), active_mask=np.zeros(6),
                               cost=0.0, x=np.ones(6))
        info, stderr = diagnostics(best, [best], curves, curves.sum(axis=0), None, None)
        self.assertIn("weak_identifiability", info["flags"])
        self.assertIn("high_component_overlap", info["flags"])
        self.assertIsNone(stderr)

    def test_irregular_sampling_fits_original_points_and_custom_baseline(self):
        x = np.sort(np.random.default_rng(3).uniform(0, 3, 401))
        baseline = np.interp(x, [x[0], 1.27, x[-1]], [.1, .18, .12])
        y = baseline + .7 * np.exp(-.5 * ((x - 1.5) / .19) ** 2) / (.19 * np.sqrt(2 * np.pi))
        editor = PeakEditor(x, y)
        editor.insert_peak("p", .25, 2.75, baseline="custom", knots=[[x[0], .1], [1.27, .18], [x[-1], .12]])
        fit = editor.fit_components("p", [1.5], starts=1)
        self.assertEqual(fit.metadata["diagnostics"]["sample_count"], int(np.sum((x >= .25) & (x <= 2.75))))
        self.assertAlmostEqual(fit.metadata["components"][0]["area_full_model_uV_s"], 42000, places=5)

    def test_repeated_fit_and_export_preserve_units_trace_and_residuals(self):
        editor, _ = fitting_demo()
        first = editor.fit_components("envelope", [6.8, 7.08, 7.36], starts=2)
        second = editor.fit_components("envelope", [6.8, 7.08, 7.36], starts=2)
        self.assertEqual(first.metadata, second.metadata)
        with tempfile.TemporaryDirectory() as output:
            path = first.export(output, "test")
            saved = json.loads(path.read_text())
            self.assertEqual(saved["trace_sha256"], first.metadata["trace_sha256"])
            self.assertEqual(saved["peak"]["peak_id"], "envelope")
            with (Path(output) / "test_components.csv").open(encoding="utf-8-sig") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 3)
            self.assertIn("area_window_uV_s", rows[0])
            with (Path(output) / "test_fit_curves.csv").open(encoding="utf-8-sig") as handle:
                curves = list(csv.DictReader(handle))
            self.assertEqual(len(curves), saved["diagnostics"]["sample_count"])
            self.assertIn("residual_mV", curves[0])
            self.assertTrue((Path(output) / "test_fit.svg").is_file())


if __name__ == "__main__":
    unittest.main()
