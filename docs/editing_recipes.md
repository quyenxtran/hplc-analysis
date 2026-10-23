# Editing recipes and batch use

Run the synthetic three-peak example first:

```powershell
python edit_peaks.py --demo --output editing_results/demo
python edit_peaks.py --write-example-recipe synthetic_edits.json
```

The generated recipe contains synthetic bounds and valley brackets. Inspect your
experimental trace and change them before applying it. No default recipe is
silently applied to real data.

A two-region example (illustrative times only):

```json
{
  "schema_version": 1,
  "description": "Reviewed RI overlap region",
  "initial_peaks": [
    {"peak_id": "cluster", "start_min": 6.0, "end_min": 10.0}
  ],
  "operations": [
    {"op": "split_peak", "peak_id": "cluster", "at_min": 7.6,
     "child_ids": ["region_A", "region_B"], "separation": "vertical"},
    {"op": "set_separation", "left_id": "region_A", "right_id": "region_B",
     "mode": "baseline"}
  ]
}
```

Each operation's fields are the keyword arguments documented in the Python API.
For a valley search, use `op: split_at_valley` and `between_min: [a,b]` instead
of `at_min`. The bracket must contain a genuine local minimum. Strongly
unresolved shoulders may need a reviewed explicit cut or skim instead.

Apply to one compatible LCD or to a folder:

```powershell
python edit_peaks.py sample.lcd --channel ri --recipe edits.json --output output
python edit_peaks.py "C:\path\to\LCD folder" --include "47A*.lcd" --channel ri --recipe edits.json --output output
```

Supported detector selectors are `ri`, `uv210`, and `uv254`. Use an appropriate
recipe for each detector/method; retention times and overlap geometry can differ.
Repeat `--exclude PATTERN` to skip specified files. Every included file gets an
entry in the batch manifest, including failures. Any failed file makes the CLI
exit nonzero. Review transfer of fixed windows between runs, especially if RTs
drift or a component is absent.

For generic CSV input, values must be in minutes and mV:

```powershell
python edit_peaks.py trace.csv --time-column time_min --signal-column signal_mV --recipe edits.json --output output
```

Existing three-channel exported CSVs work with `--channel` directly. The chosen
column determines the CSV trace; there is no silent unit conversion.

Each file produces:

- `*_areas.csv`: active peak IDs, µV·s areas, heights, bounds, method, and flags.
- `*_curves.csv`: signal, baseline, and allocated component curves in mV.
- `*_audit.json`: hashes, edit history, and complete peak state for replay.
- `*_comparison.svg` / `.png`: original versus edited allocation.
- `editing_manifest_CHANNEL.json`: recipe, its hash, and per-file status.

These are generated local outputs and are ignored by Git. Re-running a prefix
replaces that output set; choose a new output directory to retain old results.

The editor performs manual integration rules, not automatic multi-component
curve fitting. Splitting a signal does not confirm the number or identity of
chemical components. Baseline separation and skimming encode explicit
assumptions; inspect the plot and review flags before using the areas.
