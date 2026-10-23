"""Integrate a user-selected HPLC peak window in a Shimadzu LCD or exported CSV.

Default: original 47A0.lcd when available, otherwise the bundled sample CSV;
all detectors, 6-12 min, linear endpoint baseline.
Primary reported area unit: uV*s (Shimadzu convention); mV*min is retained.
Requires numpy, matplotlib, olefile, and the adjacent plot_hplc.py.
The window includes all signal/shoulders between its bounds; it does not separate
coeluting components, identify compounds, or reproduce vendor integration rules.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json

import numpy as np

from plot_hplc import DEFAULT_SOURCE, read_chromatograms, plt


def area_to_uv_seconds(area_mv_min):
    """Convert mV*min to uV*s: 1000 uV/mV times 60 s/min."""
    return area_mv_min * 60_000


def integrate_window(time, signal, start, end, baseline="linear"):
    """Signed trapezoidal area with interpolated boundary samples, no clipping.

    Returns raw area, baseline area and net area in signal units times minutes.
    With linear baseline, net is the area above the endpoint-to-endpoint line.
    """
    time, signal = np.asarray(time, dtype=float), np.asarray(signal, dtype=float)
    if time.ndim != 1 or signal.shape != time.shape or len(time) < 2:
        raise ValueError("Time and signal must be matching 1D arrays with at least two samples.")
    if not np.all(np.isfinite(time)) or not np.all(np.isfinite(signal)):
        raise ValueError("Time and signal must contain only finite values.")
    if not np.all(np.diff(time) > 0):
        raise ValueError("Time must be strictly increasing, with no duplicates.")
    if not np.isfinite(start) or not np.isfinite(end) or start >= end:
        raise ValueError("Bounds must be finite and start must be less than end.")
    if start < time[0] or end > time[-1]:
        raise ValueError(f"Window [{start}, {end}] lies outside sampled range [{time[0]}, {time[-1]}] min.")
    if baseline not in ("linear", "none"):
        raise ValueError("Baseline must be 'linear' or 'none'.")
    inside = (time > start) & (time < end)
    x = np.concatenate(([start], time[inside], [end]))
    y = np.interp(x, time, signal)
    base = np.interp(x, [start, end], [y[0], y[-1]]) if baseline == "linear" else np.zeros_like(y)
    corrected = y - base
    # Explicit trapezoids support both older and newer NumPy installations.
    raw_area = float(np.sum(np.diff(x) * (y[:-1] + y[1:]) / 2))
    baseline_area = float(np.sum(np.diff(x) * (base[:-1] + base[1:]) / 2))
    net_area = float(np.sum(np.diff(x) * (corrected[:-1] + corrected[1:]) / 2))
    apex = int(np.argmax(corrected))
    return {
        "time": x, "signal": y, "baseline": base, "corrected": corrected,
        "raw_area": raw_area, "baseline_area": baseline_area, "net_area": net_area,
        "apex_time_min": float(x[apex]), "height_above_baseline": float(corrected[apex]),
    }


def load_channels(source):
    if source.suffix.lower() == ".lcd":
        return read_chromatograms(source)
    if source.suffix.lower() != ".csv":
        raise ValueError("Input must be .lcd or the CSV exported by plot_hplc.py.")
    data = np.genfromtxt(source, delimiter=",", names=True, encoding="utf-8-sig")
    expected = ["time_min", "RI_mV", "UV_210nm_mV", "UV_254nm_mV"]
    if data.dtype.names is None or any(key not in data.dtype.names for key in expected):
        raise ValueError(f"CSV must have columns: {', '.join(expected)}")
    return [
        {"channel": i, "label": label, "unit": "mV", "time": data["time_min"], "signal": data[column]}
        for i, (label, column) in enumerate([
            ("Refractive index", "RI_mV"), ("UV at 210 nm", "UV_210nm_mV"), ("UV at 254 nm", "UV_254nm_mV")
        ], 1)
    ]


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
    rows = []
    for channel, result in zip(channels, results):
        rows.append({
            "channel": channel["channel"], "detector": channel["label"], "signal_unit": channel["unit"],
            "start_min": args.start, "end_min": args.end, "baseline_method": args.baseline,
            "net_area_uV_s": area_to_uv_seconds(result["net_area"]),
            "raw_area_uV_s": area_to_uv_seconds(result["raw_area"]),
            "baseline_area_uV_s": area_to_uv_seconds(result["baseline_area"]),
            "height_above_baseline_uV": result["height_above_baseline"] * 1000,
            "raw_area_mV_min": result["raw_area"], "baseline_area_mV_min": result["baseline_area"],
            "net_area_mV_min": result["net_area"], "net_area_mV_s": result["net_area"] * 60,
            "apex_time_min": result["apex_time_min"], "height_above_baseline_mV": result["height_above_baseline"],
            "baseline_start_mV": float(result["baseline"][0]), "baseline_end_mV": float(result["baseline"][-1]),
        })
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

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "svg.fonttype": "none"})
    fig, axes = plt.subplots(len(channels), 1, figsize=(10, 3 * len(channels) + 1), sharex=True, squeeze=False)
    fig.subplots_adjust(left=0.12, right=0.97, top=0.87, bottom=0.13, hspace=0.5)
    fig.suptitle(f"{stem} | Main peak integration", x=0.12, y=0.975, ha="left", fontsize=18, weight="bold")
    fig.text(0.12, 0.925, f"Window: {args.start:g}\u2013{args.end:g} min  |  Baseline: {args.baseline}  |  Signed trapezoidal area", fontsize=10)
    colors = {1: "#28649B", 2: "#A96425", 3: "#657733"}
    pad = max((args.end - args.start) * 0.12, 0.1)
    left = max(channels[0]["time"][0], args.start - pad)
    right = min(channels[0]["time"][-1], args.end + pad)
    for ax, channel, result in zip(axes[:, 0], channels, results):
        color = colors[channel["channel"]]
        visible = (channel["time"] >= left) & (channel["time"] <= right)
        ax.plot(channel["time"][visible], channel["signal"][visible], color=color, lw=1.3, label="Signal")
        ax.fill_between(result["time"], result["signal"], result["baseline"], color=color, alpha=0.2, label="Integrated region")
        ax.plot(result["time"], result["baseline"], color="#30343B", ls="--", lw=1.1, label="Baseline")
        ax.axvline(args.start, color="#777777", lw=0.8, ls=":")
        ax.axvline(args.end, color="#777777", lw=0.8, ls=":")
        ax.set_title(f"{channel['label']}  |  Net area = {area_to_uv_seconds(result['net_area']):,.0f} \u00b5V\u00b7s", loc="left", fontsize=12)
        ax.set_ylabel("Signal (mV)")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#E6E8EB", lw=0.7)
        ax.set_axisbelow(True)
        ax.margins(y=0.12)
    axes[0, 0].legend(loc="upper right", frameon=True, facecolor="white", edgecolor="none", framealpha=1, fontsize=9)
    axes[-1, 0].set_xlabel("Retention time (min)")
    axes[-1, 0].set_xlim(left, right)
    fig.text(0.12, 0.035, "Initial window includes shoulders and tail; no compound assignment or peak separation.", fontsize=9, color="#616770")
    for extension in ["png", "pdf", "svg"]:
        fig.savefig(args.output / f"{tag}_integration.{extension}", dpi=200, facecolor="white")
    plt.close(fig)
    for row in rows:
        print(f"{row['detector']}: net={row['net_area_uV_s']:,.3f} uV*s; raw={row['raw_area_uV_s']:,.3f} uV*s ({row['net_area_mV_min']:.8g} mV*min net)")
    print(f"Saved {csv_path.resolve()}")


if __name__ == "__main__":
    main()
