"""Render explicit before/after area allocations."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def plot_edit_comparison(editor, before, path, subtitle=""):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "svg.fonttype": "none"})
    fig, axes = plt.subplots(2, 1, figsize=(10, 7.5), sharex=True)
    fig.subplots_adjust(left=0.11, right=0.97, top=0.86, bottom=0.14, hspace=0.48)
    fig.suptitle(editor.label + " | Peak editing", x=0.11, y=0.97, ha="left", fontsize=17, weight="bold")
    fig.text(0.11, 0.915, subtitle or "Original signal retained | Signed areas in ÂµVÂ·s", fontsize=10, color="#5B626B")
    palette = ["#28649B", "#A96425", "#657733", "#9B4D75", "#546D85"]
    states = [before, editor.snapshot()]
    active = [p for state in states for p in state.values() if p.enabled]
    lower = min((p.start_min for p in active), default=editor.time_min[0])
    upper = max((p.end_min for p in active), default=editor.time_min[-1])
    padding = (upper - lower) * 0.06
    left, right = max(editor.time_min[0], lower - padding), min(editor.time_min[-1], upper + padding)
    visible = (editor.time_min >= left) & (editor.time_min <= right)
    for ax, state, title in zip(axes, states, ["Before", "After"]):
        ax.plot(editor.time_min[visible], editor.signal_mv[visible], color="#30343B", lw=1.2, label="Input signal")
        table = editor.peak_table(state=state)
        for index, row in enumerate(table):
            curve = editor.curve(row["peak_id"], state)
            x, base, net = curve["time_min"], curve["baseline_mv"], curve["allocated_mv"]
            color = palette[index % len(palette)]
            ax.fill_between(x, base, base + net, color=color, alpha=0.26,
                            label=f"{row['peak_id']}: {row['area_uV_s']:,.0f} ÂµVÂ·s")
            ax.plot(x, base, color=color, ls="--", lw=0.9)
            ax.axvline(row["start_min"], color=color, ls=":", lw=0.7)
            ax.axvline(row["end_min"], color=color, ls=":", lw=0.7)
        total = sum(row["area_uV_s"] for row in table)
        ax.set_title(f"{title} | {len(table)} active regions | Total allocated area: {total:,.1f} ÂµVÂ·s", loc="left", fontsize=11)
        ax.set_ylabel("Signal (mV)")
        ax.grid(axis="y", color="#E6E8EB", lw=0.7)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="none", framealpha=0.96, fontsize=8)
        ax.margins(y=0.15)
    axes[-1].set_xlim(left, right)
    axes[-1].set_xlabel("Retention time (min)")
    fig.text(0.11, 0.04, "Colored regions show the selected area-allocation rules; they do not establish separate chemical identities.", fontsize=9, color="#5B626B")
    fig.savefig(path, dpi=180, facecolor="white")
    plt.close(fig)
