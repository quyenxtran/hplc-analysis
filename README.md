# HPLC analysis

Extract Shimadzu HPLC chromatograms, plot detector traces, and integrate selected
peak windows with area reported in **µV·s**. Includes the 47A0 sample CSV, plots,
integration outputs, and numerical checks.

Requires Python 3.9+. From this repository folder:

```powershell
python -m pip install -r requirements.txt
python integrate_peak.py --start 6 --end 12
```

`integrate_peak.py` reads the original `47A0.lcd` on the author's workstation when
available, and otherwise uses the bundled `47A0_chromatograms.csv`. Both input
formats are supported explicitly. Keep it beside `plot_hplc.py`, the LCD reader.

Integrate your own LCD file:

```powershell
python integrate_peak.py "C:\path\to\sample.lcd" --start 6 --end 12
```

Select only the 210 nm detector or change the bounds:

```powershell
python integrate_peak.py --channel uv210 --start 6.2 --end 11.5
```

Specify the exported CSV explicitly:

```powershell
python integrate_peak.py 47A0_chromatograms.csv --start 6 --end 12
```

Extract and plot a compatible three-channel LCD file:

```powershell
python plot_hplc.py "C:\path\to\sample.lcd" --output output
```

Original binary `.lcd` files are excluded from Git. The included sample retains
refractive-index, 210 nm UV, and 254 nm UV traces in mV, plus raw detector counts.

To read another LCD directly, pass its full path as the first argument. The default
source is `C:\Users\qtran47\OneDrive - Georgia Institute of Technology\Aim 2 Adsorbent\3. Batch Adsorption\Batch Ads FA26\HPLC Data\26 10 22 47A1-2\47A0.lcd`.
The integration outputs have been regenerated directly from this LCD and checked
against the saved CSV from the earlier extraction.

Other options: `--channel ri|uv210|uv254|all`, `--baseline linear|none`,
and `--output PATH`. Input CSVs must follow the existing three-channel export
schema. LCD input is limited to this reader's three-channel layout with mV units.
For a complete CLI reference use `--help`.

## Calculation

- Bounds are in minutes and must be inside the sampled range. Boundary values
  are linearly interpolated when they fall between acquired samples.
- Raw area is the signed trapezoidal integral of the signal over the window.
- The default baseline is the straight line joining signal values at the two
  endpoints. Baseline area is its integral over the same window.
- Net area = raw area - baseline area. Negative portions are retained, with no
  clipping or smoothing. `--baseline none` integrates against zero.
- The primary reported area unit is µV·s, matching Shimadzu's unit convention.
  Conversion: **area (µV·s) = area (mV·min) × 60,000**. Console output and plot
  titles use this unit. The CSV and JSON include `net_area_uV_s`,
  `raw_area_uV_s`, and `baseline_area_uV_s`; previous mV·min and mV·s columns
  are retained. Corrected peak height is also included in µV.
- The first-pass 6–12 minute window contains the dominant peak envelope,
  including shoulders and tail. These are initial manual bounds, not automated
  peak detection. Endpoint baseline subtraction can remove residual tail signal;
  inspect the plot and adjust the bounds to your integration protocol.
- These areas are not compound-specific quantities and do not establish
  concentration without an appropriate calibration. Vendor integration may use
  different baseline and peak-separation rules. Matching units does not reproduce
  Chromatopac integration boundaries or its baseline algorithm. For the default
  RI window, the script gives about 302,798 µV·s; the screenshot reports 303,175.

## Outputs

The default `peak_area/` directory receives a summary CSV (raw, baseline and net
area; apex time; corrected height), pointwise integration CSV, provenance JSON,
and shaded PNG/PDF/SVG plots. Filenames include bounds, detector selection and
baseline method. Re-running identical parameters replaces that output set.

LCD time values use the stored 500 ms sampling interval; the last sample is at
14.9916667 minutes. Stored calibration and value factors provide signal scaling,
using the file's mV display setting. The binary reader follows the publicly
documented [chromConverter format implementation](https://github.com/ethanbass/chromConverter/blob/master/R/read_shimadzu_lcd.R).

Numerical and source-consistency checks:

```powershell
python -m unittest discover -s . -p test_integrate_peak.py -v
```

The direct LCD-versus-CSV comparison is skipped when the original LCD is absent.
