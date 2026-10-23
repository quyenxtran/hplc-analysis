# Overlapping component fitting

Fit positive Gaussian or exponentially modified Gaussian (EMG) components to a
reviewed envelope, even when there is no local valley. Choose 1–6 component
center estimates; their count is the requested number of components. No acid
identification or automatic component-count inference is performed.

```powershell
python -m pip install -r requirements.txt
python fit_peaks.py --demo --output editing_results/overlap_demo
python fit_peaks.py sample.lcd --channel ri --window 6 9 --centers 6.8 7.1 --model emg --baseline-values 0.02 0.03 --output editing_results/sample
```

The default baseline connects the measured window endpoints. Review it: endpoints
inside a peak can underestimate area. `--baseline-values` supplies reviewed mV
values. `--baseline zero` or `horizontal` are also available. Custom CSV column
names use `--time-column` and `--signal-column`. All input times are minutes and
signals mV. There is no automatic RT cutoff for explicit fitting windows.

## Python API

```python
from edit_peaks import load_editor

editor = load_editor("sample.lcd", channel="ri")
editor.insert_peak("envelope", 6, 9, start_mv=0.02, end_mv=0.03)
fit = editor.fit_components(
    "envelope", centers_min=[6.8, 7.1], model="emg",
    center_tolerance_min=0.2, starts=5)
print(fit.metadata["components"])
print(fit.metadata["diagnostics"])
fit.export("editing_results/sample", prefix="sample_ri")
```

The envelope must be active and have no skim allocations. Existing custom
baseline knots are supported and held fixed. Fitting never changes manual peak
states, edit history, or the raw trace. Fit results are separate model estimates.

## Models and optimization

Gaussian parameters: full area, location µ, and standard deviation σ. EMG adds a
positive exponential tail time τ; its shape uses `K=τ/σ`. For EMG, location µ is
the underlying Gaussian location, **not the observed apex**. Both are exported.

The solver uses SciPy bounded unweighted least squares on original samples only.
It scales time/signal, constrains positive areas/widths, and runs deterministic
multistart initialization (seed 47). Each Gaussian location stays within the
midpoints of adjacent initial locations; optional tolerance narrows these bounds.
EMG uses the same location bounds, so enter estimates for µ, not tailing apices.
Changing seeds can change the solution. Nonconverged runs are discarded; if all
fail, the request fails without changing manual edits. No smoothing or negative
signal clipping is applied to the fit residuals.

## Areas and diagnostics

| Output | Meaning |
|---|---|
| `area_window_uV_s` | Analytic model integral inside the reviewed envelope. |
| `area_full_model_uV_s` | Model integral from minus to plus infinity, including extrapolated tails. |
| `fraction_in_window` | Fraction of the full model area captured by the window. |
| `area_full_model_se_uV_s` | Local conditional standard error, or unavailable for constrained/ambiguous fits. |
| RMSE and residual curve | How closely the model reproduces the measured signal. |

Window diagnostics also report measured and fitted total areas; residual area
is their difference over the exact selected window, using the reviewed baseline.

Flags cover poor fits, boundary solutions, truncated/undersampled components,
large conditional area uncertainty, correlated components, ill-conditioned
Jacobians, and alternative multistart area solutions. The conditional-uncertainty
flag uses a relative area standard error above 5%. Checks are heuristic; absence
of a flag does not establish uniqueness. Exactly coeluting components
cannot generally be resolved without additional information such as standards.
Standard errors assume the selected count/model/baseline and independent,
equal-variance errors; they omit baseline/model uncertainty and noise correlation.

Exports: component CSV, sampled model/residual CSV, fit/residual SVG, and JSON
provenance with trace hash, baseline, editing history, configuration, parameters,
units, diagnostics, and NumPy/SciPy versions. Numerical fits may change slightly
between SciPy versions. Fit curves cover original samples within the window;
analytic window integrals include the exact requested endpoints.

References: [SciPy least_squares](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html)
and [SciPy exponnorm](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.exponnorm.html).
