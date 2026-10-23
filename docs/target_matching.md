# Target matching

Use `match_acid_peaks.py` for detector-specific target windows. The default
minimum RT is **5 min**, with no fixed upper cutoff for discovery:

```powershell
python match_acid_peaks.py "C:\path\to\LCD folder" --output batch_results\discovery
```

This writes `discovered_peaks.csv` (all positive saved peaks at/after 5 min,
including a filter flag) and `large_peaks_after_cutoff.csv` (area ≥1000 µV·s
and ≥1% of the largest late peak per file/detector). Discovery assigns no acid
names. Change the cutoff with `--min-retention-time`.

For named targets, prepare a CSV with these columns:

```csv
target_name,detector,expected_rt_min,tolerance_min,min_area_uV_s
unidentified_47A0_peak,RI,7.1463,0.15,1000
unidentified_47A0_peak,UV_210nm,6.8845,0.15,1000
unidentified_47A0_peak,UV_254nm,6.8830,0.15,1000
```

These are provisional demonstration windows, not chemical identifications or
validated tolerances. Replace them with standard-derived times and appropriate
tolerances under your method. Add rows for any number of acids; each acid may
use different expected RTs and area thresholds on each detector. Supported
detector keys are `RI`, `UV_210nm`, and `UV_254nm`. The 5-minute cutoff applies
to targets too; lower it explicitly if a target elutes earlier.

Generate the example locally and run:

```powershell
python match_acid_peaks.py --write-example-targets targets.csv
python match_acid_peaks.py "C:\path\to\LCD folder" --targets targets.csv --output batch_results\targets
```

`target_matches.csv` contains one row per file/target/detector. A match needs
exactly one positive peak above that target's absolute minimum within its
expected RT ± tolerance. Missing matches, multiple candidates, and peaks
claimed by two targets are flagged with blank reported areas. This avoids
automatically substituting the largest unrelated peak. `target_candidates.csv`
retains candidates for review; `matching_metadata.json` records configuration,
file hashes, and errors. RT matching is a candidate assignment and does not
confirm chemical identity.

**The relative-area filter applies only to discovery.** Target matching uses
each acid's own absolute threshold, so an abundant acid does not suppress a
weaker acid. Areas retain Shimadzu's saved integration bounds and µV·s units;
shoulders are not deconvolved.

Use `--include "47A*.lcd"` to restrict the current example to experiment-named
files, or repeat `--exclude "wait.lcd"` / other patterns as needed. Files are
included by default; no name is automatically assumed to be a blank or wash.
