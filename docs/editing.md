# Manual peak editing API

The editor operates on one detector trace in minutes and mV. It retains the raw
arrays and integrates signed piecewise-linear curves; area in mV·min is
multiplied by 60,000 to report µV·s. Peak IDs are labels, not chemical identities.

```python
from peak_editor import PeakEditor
from edit_peaks import load_editor

editor = load_editor("sample.lcd", channel="ri")
# Illustrative bounds only: inspect and adjust for your method/detector.
editor.insert_peak("cluster", 6.0, 10.0)
editor.split_peak("cluster", at_min=7.6, child_ids=["left", "right"])
editor.set_baseline("left", mode="horizontal", start_mv=0.02)
editor.undo()
editor.redo()
editor.export("output", prefix="sample_ri", source="sample.lcd")
```

Generic input: `PeakEditor(time_min, signal_mv, label="Sample")`.

| Operation | Meaning |
|---|---|
| `insert_peak(id, start, end, baseline=...)` | Add an integration region; baseline is linear by default. |
| `move_baseline(id, start_min=..., end_min=..., start_mv=..., end_mv=...)` | Move time/intensity endpoints. Moved times snap to the signal unless intensity is explicit; unchanged endpoints retain their intensity. This replaces custom knots with a line. |
| `set_baseline(id, mode=...)` | Use linear, horizontal, zero, or custom knots. |
| `split_peak(id, at_min, child_ids=...)` | Divide one envelope at an explicit time. |
| `split_n_peaks(id, split_times, child_ids=...)` | Divide it into two, three, or more regions. |
| `split_at_valley(id, between_min=[a,b], ...)` | Find a real local minimum inside a reviewed bracket; fail if no valley exists. |
| `unify_peaks(ids, new_id, baseline=...)` | Merge adjacent regions. `outer` redraws the line between outer endpoints; `preserve` requires contiguous regions sharing exactly one baseline. |
| `set_separation(left_id, right_id, mode=...)` | Change adjacent regions between vertical and baseline separation. |
| `reject_peak(id)` / `restore_peak(id)` | Remove/restore a reported region without modifying raw data. |
| `skim_peak(parent_id, id, start, end, ...)` | Allocate a rider on a tail or leading edge above a linear/custom baseline. |
| `remove_skim(id)` | Return a skim allocation to its parent. |
| `undo()` / `redo()` | Restore prior edit states; new edits clear redo history. |

## Baselines and overlaps

`linear` connects endpoint signal values, or explicit `start_mv`/`end_mv`.
`horizontal` uses `start_mv` (or the start signal value). `zero` uses zero.
A custom baseline uses `mode="custom", knots=[[time, mV], ...]`; knots must
increase in time and cover the peak window. Off-grid bounds and knots are
included exactly in integration.

**Vertical separation** partitions an envelope over its existing common
baseline and conserves its total area. **Baseline separation** draws individual
lines through the split/valley signal, so the assigned total can change.

A skim allocates the signed residual above its chosen baseline to the rider and
subtracts it from the host. Host plus riders preserves the original envelope
area. This is a manual allocation, not an exponential-tail fit or chemical
deconvolution. Skim windows cannot overlap each other or be nested. Remove skims
before splitting/merging their host.

Rejecting a rider excludes its reported area but does not silently reassign it
to the host; use `remove_skim` to reclaim it. Rejecting a host also rejects its
riders. Restoring a host does not automatically restore rejected riders.

## Results, review, and resuming

`peak_table()` returns active regions; `include_rejected=True` also shows
rejected states. Flags include a baseline crossing the signal, nonpositive
area, a skim below the host baseline, and acquisition-boundary contact. These
are review flags, not automatic corrections. Failed operations leave state
and history unchanged.

Exports include active-region areas, pointwise allocated curves, and a JSON
audit with source/trace hashes, operations, parameters, and before/after states.
Repeated times in skim curves encode discontinuous boundaries with zero-width
steps, so the curves integrate to the reported areas without boundary leakage.

```python
resumed = PeakEditor.from_audit(editor.time_min, editor.signal_mv,
                               "output/sample_ri_audit.json")
```

Resuming checks the trace hash and replayed final state before accepting the
session. Input units must remain minutes/mV. Original LCD files are never edited.
