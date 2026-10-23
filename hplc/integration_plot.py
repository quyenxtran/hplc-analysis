"""Shaded integration diagnostic figures."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .integration import area_to_uv_seconds

def plot_integration(channels, results, start, end, baseline, stem, output, tag):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "svg.fonttype": "none"})
    fig, axes = plt.subplots(len(channels), 1, figsize=(10, 3 * len(channels) + 1), sharex=True, squeeze=False)
    fig.subplots_adjust(left=0.12, right=0.97, top=0.87, bottom=0.13, hspace=0.5)
    fig.suptitle(f"{stem} | Main peak integration", x=0.12, y=0.975, ha="left", fontsize=18, weight="bold")
    fig.text(0.12, 0.925, f"Window: {start:g}\u2013{end:g} min  |  Baseline: {baseline}  |  Signed trapezoidal area", fontsize=10)
    colors = {1: "#28649B", 2: "#A96425", 3: "#657733"}
    pad = max((end - start) * 0.12, 0.1)
    left = max(channels[0]["time"][0], start - pad)
    right = min(channels[0]["time"][-1], end + pad)
    for ax, channel, result in zip(axes[:, 0], channels, results):
        color = colors[channel["channel"]]
        visible = (channel["time"] >= left) & (channel["time"] <= right)
        ax.plot(channel["time"][visible], channel["signal"][visible], color=color, lw=1.3, label="Signal")
        ax.fill_between(result["time"], result["signal"], result["baseline"], color=color, alpha=0.2, label="Integrated region")
        ax.plot(result["time"], result["baseline"], color="#30343B", ls="--", lw=1.1, label="Baseline")
        ax.axvline(start, color="#777777", lw=0.8, ls=":")
        ax.axvline(end, color="#777777", lw=0.8, ls=":")
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
        fig.savefig(output / f"{tag}_integration.{extension}", dpi=200, facecolor="white")
    plt.close(fig)
