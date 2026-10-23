"""Plot compatible three-channel Shimadzu LCD data; supply a source path."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import olefile
from hplc.defaults import DEFAULT_SOURCE
from hplc.lcd import read_xml, read_float, decode_chromatogram, read_chromatograms

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    channels = read_chromatograms(args.source)
    data_path = output / f"{args.source.stem}_chromatograms.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time_min", "RI_mV", "UV_210nm_mV", "UV_254nm_mV", "RI_raw_counts", "UV_210nm_raw_counts", "UV_254nm_raw_counts"])
        for index, time in enumerate(channels[0]["time"]):
            writer.writerow([f"{time:.10f}"] + [f"{c['signal'][index]:.12g}" for c in channels] + [int(c["counts"][index]) for c in channels])

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "axes.labelcolor": "#30343B", "text.color": "#30343B",
                         "axes.edgecolor": "#8B9097", "svg.fonttype": "none"})
    fig, axes = plt.subplots(3, 1, figsize=(10, 8.5), sharex=True)
    fig.subplots_adjust(left=0.13, right=0.97, top=0.88, bottom=0.12, hspace=0.48)
    fig.suptitle(f"{args.source.stem} | HPLC chromatograms", x=0.13, y=0.975, ha="left", fontsize=18, weight="bold")
    fig.text(0.13, 0.93, "15 min run  |  0.5 s sampling  |  1,800 points per detector", fontsize=11, color="#616770")
    colors = ["#28649B", "#A96425", "#657733"]
    for ax, channel, color in zip(axes, channels, colors):
        ax.plot(channel["time"], channel["signal"], color=color, linewidth=1.3)
        ax.set_title(f"{channel['label']}  ({channel['detector']})", loc="left", fontsize=12, pad=9)
        ax.set_ylabel(f"Signal ({channel['unit']})")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#E6E8EB", linewidth=0.7)
        ax.set_axisbelow(True)
        ax.margins(y=0.12)
        ax.tick_params(axis="both", labelsize=10)
    axes[-1].set_xlim(0, max(c["run_stop_min"] for c in channels))
    axes[-1].set_xticks([0, 3, 6, 9, 12, 15])
    axes[-1].set_xlabel("Retention time (min)")
    fig.text(0.13, 0.035, "Original signals; no smoothing or baseline correction. Units follow the file's display setting (mV).", fontsize=9, color="#616770")
    for extension in ["png", "svg", "pdf"]:
        fig.savefig(output / f"{args.source.stem}_chromatograms.{extension}", dpi=220, facecolor="white")
    plt.close(fig)

    summary = {
        "source": str(args.source), "sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        "format_reference": "https://github.com/ethanbass/chromConverter/blob/master/R/read_shimadzu_lcd.R",
        "processing": "Delta decoding and stored calibration/value factor scaling only; no smoothing, baseline correction, integration, or compound assignment.",
        "time_axis": "Start plus sample index times the 500 ms header interval; final sample 14.9916667 min; nominal run duration 15 min.",
        "channels": [],
    }
    for channel in channels:
        entry = {k: v for k, v in channel.items() if k not in ["time", "counts", "signal"]}
        apex = int(np.argmax(channel["signal"]))
        entry.update({"points": len(channel["time"]), "minimum": float(channel["signal"].min()),
                      "maximum": float(channel["signal"].max()), "maximum_time_min": float(channel["time"][apex])})
        summary["channels"].append(entry)
    (output / f"{args.source.stem}_metadata.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Saved figure and data to {output.resolve()}")

if __name__ == "__main__":
    main()
