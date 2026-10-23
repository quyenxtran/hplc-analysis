"""Recovery with noise for resolvable overlap, plus independent package imports."""
import subprocess
import sys
import unittest
import numpy as np
from peak_editor import PeakEditor


class FittingNoiseTests(unittest.TestCase):
    def test_similarly_good_multistart_solutions_with_different_areas_are_flagged(self):
        from types import SimpleNamespace
        from hplc.fitting.diagnostics import diagnostics
        x = np.linspace(0, 1, 30)
        curves = np.vstack([np.exp(-100 * (x - .25) ** 2), np.exp(-100 * (x - .75) ** 2)])
        best = SimpleNamespace(jac=np.vstack([np.eye(6)] * 5), active_mask=np.zeros(6),
                               cost=1.0, x=np.array([1, .25, .1, 1, .75, .1]))
        other = SimpleNamespace(cost=1.01, x=np.array([.6, .25, .1, 1.4, .75, .1]))
        info, stderr = diagnostics(best, [best, other], curves, curves.sum(axis=0), None, None)
        self.assertIn("alternative_area_solutions", info["flags"])
        self.assertIsNone(stderr)

    def test_resolvable_noisy_overlap_recovers_individual_areas(self):
        x = np.linspace(5.5, 8.5, 1001)
        y = .1 + .8 * np.exp(-.5 * ((x - 6.7) / .15) ** 2) / (.15 * np.sqrt(2 * np.pi))
        y += .6 * np.exp(-.5 * ((x - 7.1) / .14) ** 2) / (.14 * np.sqrt(2 * np.pi))
        y += np.random.default_rng(9).normal(0, .01, len(x))
        editor = PeakEditor(x, y)
        editor.insert_peak("p", 5.8, 8.3, start_mv=.1, end_mv=.1)
        fit = editor.fit_components("p", [6.69, 7.09], starts=3)
        np.testing.assert_allclose([r["area_full_model_uV_s"] for r in fit.metadata["components"]],
                                   [48000, 36000], rtol=.02)
        self.assertLess(fit.metadata["diagnostics"]["rmse_mv"], .012)

    def test_fitting_package_imports_before_editor_in_fresh_interpreter(self):
        result = subprocess.run([sys.executable, "-c",
            "from hplc.fitting.demo import fitting_demo; from peak_editor import PeakEditor; assert fitting_demo()[0].peaks"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
