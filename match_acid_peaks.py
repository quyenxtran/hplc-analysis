"""Discover late peaks or assign configurable acid targets: use --help."""
import argparse
import json
from pathlib import Path
from hplc.defaults import DEFAULT_SOURCE
from hplc.targets import TARGET_FIELDS, finite_number, load_targets
from hplc.target_matching import discover_peaks, match_targets
from hplc.target_export import export_folder
from hplc.csv_io import write_csv

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", nargs="?", type=Path, default=DEFAULT_SOURCE.parent)
    parser.add_argument("--targets", type=Path, help="CSV with per-acid, per-detector expected RTs and tolerances")
    parser.add_argument("--write-example-targets", type=Path, help="Write a provisional unlabeled 47A0 example CSV, then exit")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "batch_results" / "target_matching")
    parser.add_argument("--min-retention-time", type=float, default=5)
    parser.add_argument("--min-area", type=float, default=1000, help="Discovery only; target minima come from target CSV")
    parser.add_argument("--min-relative-area-percent", type=float, default=1, help="Discovery only; does not reject weaker acid targets")
    parser.add_argument("--include", default="*.lcd")
    parser.add_argument("--exclude", action="append", default=[], help="Filename/glob to skip; repeat for multiple patterns")
    args = parser.parse_args()
    try:
        if args.write_example_targets:
            if args.write_example_targets.exists():
                raise ValueError("Example target file already exists; choose another path to preserve your edits.")
            rows = [{"target_name": "unidentified_47A0_peak", "detector": key,
                     "expected_rt_min": rt, "tolerance_min": 0.15, "min_area_uV_s": 1000}
                    for key, rt in [("RI", 7.1463), ("UV_210nm", 6.8845), ("UV_254nm", 6.8830)]]
            write_csv(args.write_example_targets, rows, TARGET_FIELDS)
            print("Wrote provisional example (replace labels/times with standards):", args.write_example_targets)
            return
        targets = load_targets(args.targets) if args.targets else None
        _, _, metadata = export_folder(args.folder, args.output, targets, args.min_retention_time,
                                       args.min_area, args.min_relative_area_percent, args.include, args.exclude)
        if any(r["status"] != "ok" for r in metadata["files"]):
            raise SystemExit(1)
    except (OSError, ValueError) as error:
        parser.error(str(error))

if __name__ == "__main__":
    main()
