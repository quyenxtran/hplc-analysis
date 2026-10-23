# Interactive HPLC workbench

Start from the repository directory after installing `requirements.txt`:

```powershell
python hplc_workbench.py
python hplc_workbench.py "C:\path\to\sample.lcd" --channel ri
python hplc_workbench.py "C:\path\to\LCD folder" --output editing_results/my_session
```

With no input, the editor opens a clearly labeled synthetic overlapping-peak
example. Otherwise it loads an LCD or numeric CSV. A folder provides a file
selector; switch between RI, UV210, and UV254 with the detector control, then
click **Load selected file**. Changing file/detector starts a fresh manual session.
Export before switching. Generic CSV uses `time_min` and `signal_mV`, or the
standard detector columns used by the extraction tools.

The server binds only to `127.0.0.1` and opens your browser. It prints a local
session URL; keep that URL private. No third-party scripts or cloud uploads are
used. `--no-browser` prints the URL without opening a browser. `--port 8765`
selects a port; the default chooses an available port. Ctrl+C stops the server.

## Review and edit

Use **Manual edits** for integration controls and **Fit components** for fitting.

1. Choose **Drag new peak window**, drag across the chromatogram, review the
   populated time/intensity fields, and click **Insert window**. New windows are
   explicit; early solvent peaks are not silently excluded or integrated.
2. Select a peak in the graph, table, or dropdown. Drag either round baseline
   endpoint in **Select / drag endpoints** mode. Dragging changes both retention
   time and baseline intensity. Numeric fields plus **Apply endpoints** provide
   the same operation; edits that overlap another active root are rejected.
3. Choose linear, horizontal, zero, or custom baseline. Custom knots use
   `time,mV; time,mV; ...` and must cover the window. Moving an endpoint replaces
   a custom baseline with a line, matching the manual API behavior.
4. Split at a typed cut, click a split on the graph, or supply a valley bracket.
   Choose vertical/shared baseline or baseline-through-cut separation. Check
   rows to merge or change the separation of an adjacent pair. Merge uses the
   outer endpoints to form a new baseline.
5. For a rider, keep its host selected, enter/draw the smaller window and skim
   endpoints, then click **Skim inside selected**. Reject/restore and remove-skim
   follow the rules in [manual editing](editing.md).

Undo/redo applies to manual edits. Zoom by dragging with **Drag to zoom**; reset
restores the full time range. The signal is never altered. All graph actions
except zoom/seed placement have corresponding numeric/table controls.

## Fit overlapping components

Select one unsplit envelope and review its baseline. Choose Gaussian or EMG,
then enter 1–6 increasing center estimates. Alternatively clear the centers
field and use **Click component seed** to collect them. EMG centers are Gaussian
locations, not observed apices. Optional tolerance narrows location bounds.
Click **Fit selected envelope** to inspect the sum, components, residuals,
diagnostic flags, and separate window/full-area table. See [fitting rules and
uncertainty](component_fitting.md). Reject/revise fits that do not represent the
data. Fitted curves are model estimates, not additional manual peaks.

Manual edits, undo/redo, changing files, or restoring audits clear stale fits.
A failed fit clears the old preview. Fitting is not part of manual undo history;
rerun it when needed. Refresh keeps the running server session; multiple tabs
share it and stale revisions are refused. Closing the server loses unexported
work. Browser close warnings are best effort; export explicitly.

## Export and resume

**Export session + fit** writes timestamped manual-area CSV, allocated curves,
audit JSON, and the current fit's CSV/JSON/SVG outputs to the server output folder.
All measurements/results stay ignored by Git. Raw LCD/CSV inputs are not modified.
Manual and model areas use different files and should not be added together.

Reload the same trace and select its saved audit in **Restore audit**, or launch:

```powershell
python hplc_workbench.py sample.lcd --channel ri --audit editing_results/session_audit.json
```

Trace hashes and replayed states are checked before restoring. Fits are exported
separately; rerun their recorded settings after restoring the manual envelope.
