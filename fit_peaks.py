"""Fit positive Gaussian/EMG mixtures with an explicit reviewed baseline."""
import argparse
from pathlib import Path
from hplc.editing.input import load_editor, CHANNELS
from hplc.fitting.demo import fitting_demo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path)
    parser.add_argument("--channel", choices=CHANNELS, default="ri")
    parser.add_argument("--window", type=float, nargs=2, metavar=("START", "END"))
    parser.add_argument("--centers", type=float, nargs="+")
    parser.add_argument("--model", choices=["gaussian", "emg"], default="gaussian")
    parser.add_argument("--center-tolerance", type=float)
    parser.add_argument("--baseline", choices=["linear", "zero", "horizontal"], default="linear")
    parser.add_argument("--baseline-values", type=float, nargs=2, metavar=("START_MV", "END_MV"))
    parser.add_argument("--time-column", default="time_min")
    parser.add_argument("--signal-column")
    parser.add_argument("--starts", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path("editing_results/fits"))
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    try:
        if args.demo:
            if args.source or args.window or args.centers or args.baseline_values:
                raise ValueError("Demo supplies its own signal, bounds, centers, and baseline.")
            editor, parameters = fitting_demo()
            centers = parameters[:, 1].tolist()
        else:
            if not args.source or not args.window or not args.centers:
                raise ValueError("Provide source, --window, and --centers, or use --demo.")
            editor = load_editor(args.source, args.channel, args.time_column, args.signal_column)
            extra = dict(zip(["start_mv", "end_mv"], args.baseline_values)) if args.baseline_values else {}
            editor.insert_peak("envelope", *args.window, baseline=args.baseline, **extra)
            centers = args.centers
        result = editor.fit_components("envelope", centers, args.model, args.center_tolerance, args.starts)
        path = result.export(args.output)
        print("Fit results:", path.resolve())
        print("Diagnostic flags:", result.metadata["diagnostics"]["flags"] or "none")
        for row in result.metadata["components"]:
            print(row["component_id"], "window area (uV*s):", row["area_window_uV_s"])
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
