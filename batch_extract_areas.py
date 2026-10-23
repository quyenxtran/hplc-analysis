"""Export exact saved Shimadzu peak areas; use --help."""
import argparse
from pathlib import Path
from hplc.defaults import DEFAULT_SOURCE
from hplc.sorting import natural_key
from hplc.saved_peaks import parse_peak_table, read_saved_peaks
from hplc.filters import filter_peaks, select_main_peak
from hplc.csv_io import write_csv
from hplc.batch import extract_folder

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", nargs="?", type=Path, default=DEFAULT_SOURCE.parent)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "batch_results" / "26_10_22_47A1-2_filtered")
    parser.add_argument("--start", type=float, default=5)
    parser.add_argument("--end", type=float, default=12)
    parser.add_argument("--min-retention-time", type=float, default=5,
                        help="Exclude peak apex times below this many minutes, even if --start is earlier (default: 5)")
    parser.add_argument("--min-area", type=float, default=1000, help="Minimum saved area in uV*s (default: 1000)")
    parser.add_argument("--min-relative-area-percent", type=float, default=1,
                        help="Minimum percent of largest positive peak per file/detector in the apex window; 0 disables (default: 1)")
    args = parser.parse_args()
    try:
        _, _, metadata = extract_folder(args.folder, args.output, args.start, args.end, args.min_area, args.min_relative_area_percent, args.min_retention_time)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    if metadata["failed_files"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
