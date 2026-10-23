"""Extract and plot the three acquired chromatograms in 47A0.lcd.

Requires numpy, matplotlib, and olefile. Run with optional source and output paths.
Format reference: https://github.com/ethanbass/chromConverter/blob/master/R/read_shimadzu_lcd.R
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import struct
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import olefile


DEFAULT_SOURCE = Path(r"C:\Users\qtran47\OneDrive - Georgia Institute of Technology\Aim 2 Adsorbent\3. Batch Adsorption\Batch Ads FA26\HPLC Data\26 10 22 47A1-2\47A0.lcd")


def read_xml(raw):
    # This instrument writes ASCII XML with some null padding/UTF-16 sections.
    text = raw.replace(b"\x00", b"").decode("latin1")
    return ET.fromstring(text[text.index("<GUD"):text.index("</GUD>") + 6])


def read_float(text):
    return struct.unpack("<d", bytes.fromhex(text))[0]


def decode_chromatogram(raw):
    label, interval_ms, count, total_bytes, _, _ = struct.unpack_from("<6I", raw)
    assert label == 17234 and total_bytes == len(raw)
    position = 24
    values = []
    while len(values) < count:
        size = struct.unpack_from("<H", raw, position)[0]
        position += 2
        payload = raw[position:position + size]
        position += size
        end_size = struct.unpack_from("<H", raw, position)[0]
        position += 2
        assert size == end_size and len(payload) == size
        i, accumulated = 0, 0
        while i < size:
            first = payload[i]
            if first == 0x82:
                i += 1
                continue
            sign = first >> 4
            if sign >= 8:
                raise ValueError("Unsupported delta record")
            width = 1 + sign // 2
            assert i + width <= size
            delta = first & 15
            for byte in payload[i + 1:i + width]:
                delta = delta * 256 + byte
            if sign % 2:
                delta -= 2 ** (8 * width - 4)
            accumulated += delta
            values.append(accumulated)
            i += width
    assert len(values) == count and position == len(raw)
    return np.asarray(values, dtype=np.int64), interval_ms


def read_chromatograms(source):
    """Read acquired detector channels without writing any files."""
    channels = []
    with olefile.OleFileIO(source) as compound:
        metadata = read_xml(compound.openstream(["LSS Raw Data", "2D Data Item"]).read())
        status = compound.openstream(["LSS Raw Data", "Chromatogram Status"]).read()
        detectors = [node for node in metadata.findall("DII") if ".CH#" in node.findtext("DSID", "")]
        for node in detectors:
            channel = int(node.findtext("CN"))
            stream = ["LSS Raw Data", f"Chromatogram Ch{channel}"]
            raw = compound.openstream(stream).read()
            counts, interval = decode_chromatogram(raw)
            record = status[(channel - 1) * 64:channel * 64]
            cf, gain, vf = struct.unpack_from("<3d", record, 16)
            unit = record[40:64].split(b"\x00")[0].decode("ascii")
            assert cf > 0 and vf > 0 and gain == 1
            assert np.isclose(cf, read_float(node.findtext("CF")))
            axis = node.find("./DDI/Axis[@ID='0']")
            selected = axis.find(f"US[@ID='{axis.attrib['DUS']}']")
            assert selected.findtext("Unit") == unit
            assert np.isclose(read_float(selected.findtext("VF")), vf)
            assert int(node.findtext("Rate")) == interval
            start_ms = read_float(node.findtext("DLT"))
            stop_ms = read_float(node.findtext("AT"))
            # Use actual sampling interval, rather than stretching the last point to stop time.
            time = (start_ms + np.arange(len(counts)) * interval) / 60000
            assert time[-1] <= stop_ms / 60000
            wavelength = node.findtext("ADN", "")
            title = "Refractive index" if node.findtext("DSN").startswith("RID") else f"UV at {wavelength.replace('nm', ' nm')}"
            signal = counts * cf / vf
            channels.append({
                "channel": channel, "detector": node.findtext("DSN"), "label": title,
                "wavelength": wavelength or None, "unit": unit, "calibration_factor": cf,
                "value_factor": vf, "gain_factor": gain, "interval_ms": interval,
                "run_stop_min": stop_ms / 60000, "time": time, "counts": counts, "signal": signal,
            })

    assert len(channels) == 3
    assert all(np.array_equal(c["time"], channels[0]["time"]) for c in channels)
    return channels


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
