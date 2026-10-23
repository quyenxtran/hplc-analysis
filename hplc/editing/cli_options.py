"""Options for reproducible HPLC peak-edit recipes."""
import argparse
from pathlib import Path
from .input import CHANNELS

def make_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path)
    parser.add_argument("--recipe", type=Path)
    parser.add_argument("--channel", choices=CHANNELS, default="ri")
    parser.add_argument("--time-column", default="time_min")
    parser.add_argument("--signal-column", help="CSV signal column; values must be in mV")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "editing_results")
    parser.add_argument("--include", default="*.lcd", help="Filename glob for folder input")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--demo", action="store_true", help="Run a clearly labeled synthetic three-peak demonstration")
    parser.add_argument("--demo-svg", type=Path, help="Additional SVG destination, only with --demo")
    parser.add_argument("--write-example-recipe", type=Path, help="Write the synthetic example recipe and exit")
    return parser
