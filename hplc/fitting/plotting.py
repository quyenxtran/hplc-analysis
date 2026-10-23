"""Standalone fit/residual figure; backend independent for browser server use."""
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg


def plot_fit(result, path):
    figure = Figure(figsize=(10, 6), constrained_layout=True)
    FigureCanvasAgg(figure)
    ax, residual = figure.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    c = result.curves
    x, base = c["time_min"], c["baseline_mV"]
    ax.plot(x, c["signal_mV"], color="#172b3a", label="Input signal", lw=1.3)
    ax.plot(x, base + c["fitted_net_mV"], color="#b64524", label="Model sum", lw=1.3)
    ax.plot(x, base, color="#687885", label="Fixed baseline", ls="--")
    for key, values in c.items():
        if key.startswith("component_"):
            ax.plot(x, base + values, label=key.removesuffix("_mV"))
    residual.plot(x, c["residual_mV"], color="#172b3a", lw=1)
    residual.axhline(0, color="#687885", ls="--", lw=0.7)
    residual.set(xlabel="Retention time (min)", ylabel="Residual (mV)")
    ax.set(ylabel="Signal (mV)", title=result.metadata["label"] + " | Model-based components")
    ax.legend(fontsize=8, ncol=3)
    flags = ", ".join(result.metadata["diagnostics"]["flags"]) or "No diagnostic flags"
    figure.suptitle(flags, fontsize=9)
    figure.savefig(path)
