# Plotting and numerical integration

```powershell
python plot_hplc.py "C:\path\to\sample.lcd" --output output
```

Exports detector traces, raw counts, metadata, and PNG/PDF/SVG plots. This reader
supports the three-channel RI, 210 nm UV, and 254 nm UV layout used by 47A0.
Time uses the recorded sampling interval; mV scaling follows the file's stored
calibration and value factors. The plotting layout is configured for the
demonstration's 15 minute run.

![Example chromatograms](../demo/chromatograms.svg)

## Calculate areas with adjustable bounds

```powershell
python integrate_peak.py "C:\path\to\sample.lcd" --start 6 --end 12
python integrate_peak.py "C:\path\to\sample.lcd" --channel uv210 --start 6.2 --end 11.5
python integrate_peak.py output\sample_chromatograms.csv --start 6 --end 12
```

Accepts compatible LCD files or the exported three-channel CSV. Supply an input
path; the optional default points to the author's local 47A0 data. Other options
are `--channel ri|uv210|uv254|all`, `--baseline linear|none`, and `--output PATH`.

The script uses signed trapezoidal integration with interpolated boundary
samples. Its default baseline joins signal values at the endpoints; negative
portions are retained without clipping or smoothing. `--baseline none` uses a
zero baseline. Outputs include raw, baseline, and net areas, pointwise curves,
provenance JSON, and shaded plots.

**Area (µV·s) = area (mV·min) × 60,000.** Older mV·min and mV·s fields are also
retained. The default 6–12 min window includes shoulders and tail. This calculated
area can differ from saved Shimadzu results because baseline and boundary rules
differ: 47A0's RI example gives about 302798 µV·s with these settings. Areas do
not establish compound identity or concentration without appropriate calibration.
