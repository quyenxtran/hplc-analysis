# Saved Shimadzu peak areas

```powershell
python batch_extract_areas.py "C:\path\to\LCD folder" --output batch_results
```

The legacy batch filter keeps saved peaks with an apex in **5–12 min**,
area **≥1000 µV·s**, and area **≥1%** of the largest positive saved peak in
that window, separately for each file/detector. Both thresholds must pass.
The 1000 minimum matches the illustrated Shimadzu setting. The extra 1% rule
is a stricter reporting choice; that relative-area control is inactive in the
screenshot. Existing saved tables already exclude areas below 1000.

A separate **5 min minimum retention time** excludes peaks with an apex below
5 min, including when `--start` is set earlier. Peaks at exactly 5 min can pass.
The effective lower bound is `max(--start, --min-retention-time)`. The default
5–12 min selection includes eligible late peaks. Override the floor with
`--min-retention-time VALUE` (set it to 0 to disable early-peak exclusion).
The unfiltered `all_saved_peak_areas.csv` remains the complete source archive.

```powershell
python batch_extract_areas.py "C:\path\to\LCD folder" --min-area 1000 --min-relative-area-percent 1
```

Use `--min-relative-area-percent 0` to disable relative filtering. Thresholds
filter saved peak records; they do not rerun Chromatopac width/slope detection
or separate shoulders from a main peak. `integrate_peak.py` still integrates
the full selected signal window, including shoulders and tail.

This reads the vendor's saved `LSS Data Processing/PT-*` peak tables directly,
retaining their original area precision and integration bounds.

- `all_saved_peak_areas.csv`: every saved peak, with filename, detector,
  retention time, area (µV·s), height (µV), and integration start/end times.
- `large_peak_areas.csv`: only saved peaks passing the time/area filters, with
  the effective threshold and each retained peak's percent of the largest peak.
- `main_peak_areas.csv`: one row per file, with RI and 210/254 nm UV columns.
  For each detector, selects the largest positive saved area whose apex is in
  5–12 min and passing both area filters. `--start` and `--end` change the
  selection window, preserving the saved integration bounds. Candidate counts
  now report peaks passing all filters. Missing/rejected peaks are blank, with
  explicit statuses.
- `extraction_metadata.json`: source hashes, coverage, method, and errors.

Save changes in LabSolutions before exporting to capture updated integration
results. For the 47A0 demonstration, the saved RI area is 303175.434 µV·s.
