"""Integrate an LCD/CSV window in uV*s; use --help."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
from hplc.defaults import DEFAULT_SOURCE
from hplc.integration import area_to_uv_seconds, integrate_window, load_channels
from hplc.integration_plot import plot_integration
from hplc.integration_reporting import area_rows

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_input = DEFAULT_SOURCE if DEFAULT_SOURCE.is_file() else Path(__file__).with_name("47A0_chromatograms.csv")
    parser.add_argument("source", nargs="?", type=Path, default=default_input)
    parser.add_argument("--start", type=float, default=6.0, help="Start in minutes (default: 6)")
    parser.add_argument("--end", type=float, default=12.0, help="End in minutes (default: 12)")
    parser.add_argument("--baseline", choices=["linear", "none"], default="linear")
    parser.add_argument("--channel", choices=["all", "ri", "uv210", "uv254"], default="all")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "peak_area")
    args = parser.parse_args()
    try:
        channels = load_channels(args.source)
        selected = {"ri": 1, "uv210": 2, "uv254": 3}.get(args.channel)
        channels = [c for c in channels if selected is None or c["channel"] == selected]
        if not channels or any(c["unit"] != "mV" for c in channels):
            raise ValueError("This script expects the three mV detector channels used in 47A0; another display unit requires matching output labels.")
        results = [integrate_window(c["time"], c["signal"], args.start, args.end, args.baseline) for c in channels]
    except (ValueError, OSError, AssertionError) as error:
        parser.error(str(error))
    args.output.mkdir(parents=True, exist_ok=True)
    rows = area_rows(channels, results, args.start, args.end, args.baseline)
    stem = args.source.stem.replace("_chromatograms", "")
    # Parameterized filenames retain earlier integrations with different bounds.
    tag = f"{stem}_{args.channel}_{args.start:g}-{args.end:g}min_{args.baseline}"
    csv_path = args.output / f"{tag}_areas.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    with (args.output / f"{tag}_curves.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["channel", "time_min", "signal_mV", "baseline_mV", "corrected_mV"])
        for channel, result in zip(channels, results):
            writer.writerows((channel["channel"], *sample) for sample in zip(result["time"], result["signal"], result["baseline"], result["corrected"]))
    provenance = {
        "source": str(args.source.resolve()), "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        "method": "Trapezoidal integration; exact bounds linearly interpolated between samples; signed areas without clipping or smoothing.",
        "primary_area_unit": "uV*s",
        "area_conversion": "Area in uV*s = area in mV*min times 60000 (1000 uV/mV times 60 s/min).",
        "vendor_comparison": "Matches Shimadzu area units. Integration bounds, baseline and algorithm remain those selected in this script; exact numerical agreement with Chromatopac is not implied.",
        "baseline": "Line joining the signal values at integration endpoints." if args.baseline == "linear" else "Zero baseline.",
        "scope": "Total signal envelope in the selected window, including shoulders and any other peaks. Bounds are user-adjustable initial choices, not automatically identified peak boundaries.",
        "results": rows,
    }
    (args.output / f"{tag}_metadata.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")

    plot_integration(channels, results, args.start, args.end, args.baseline, stem, args.output, tag)
    for row in rows:
        print(f"{row['detector']}: net={row['net_area_uV_s']:,.3f} uV*s; raw={row['raw_area_uV_s']:,.3f} uV*s ({row['net_area_mV_min']:.8g} mV*min net)")
    print(f"Saved {csv_path.resolve()}")

if __name__ == "__main__":
    main()
