"""All graphs of a run, written to <run>/plots/.

    plots/<label>/rep01_call01.png        voltage, current, power, energy (whole recording)
    plots/<label>/rep01_call01_zoom.png   the same for the first few AC cycles
    plots/energy_per_repetition.png       energy above idle of each label, per repetition
    plots/temperature.png                 CPU temperature and waiting time before each repetition

Re-plot a run: python3 -m quarch_profiler.plots runs/<run>/
"""

import json
import sys

import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from .run_folder import RunFolder
from .settings import SAMPLE_SECONDS, ZOOM_CYCLES

SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6"


def plot_run(run, cycles=ZOOM_CYCLES):
    """Every graph of the run."""
    for csv_path in sorted(run.measurements_dir.glob("*/*_samples.csv")):
        summary = json.loads(csv_path.with_name(
            csv_path.name.replace("_samples.csv", "_summary.json")).read_text())
        samples = pd.read_csv(csv_path)
        out_dir = run.plots_dir / csv_path.parent.name
        out_dir.mkdir(exist_ok=True)
        name = csv_path.name.replace("_samples.csv", "")
        plot_measurement(samples, summary, out_dir / f"{name}.png")
        plot_measurement(first_cycles(samples, cycles), summary,
                         out_dir / f"{name}_zoom.png", zoom_cycles=cycles)
    plot_energy_per_repetition(run)
    plot_temperature(run)
    print(f"[plots] saved to {run.plots_dir}", flush=True)


# ======================================================================
# One measurement: voltage, current, power, energy
# ======================================================================

def plot_measurement(samples, summary, out_path, zoom_cycles=0):
    zoom = zoom_cycles > 0
    t = samples["t_s"] * (1000 if zoom else 1)
    fig = new_figure(4, height=9)
    ax_v, ax_i, ax_p, ax_e = fig.axes

    ax_v.plot(t, samples["L1_mV"] / 1000, color=BLUE, linewidth=1.2)
    style(ax_v, "Voltage (V)")
    ax_i.plot(t, samples["L1_mA"] / 1000, color=ORANGE, linewidth=1.2)
    style(ax_i, "Current (A)")

    ax_p.plot(t, samples["watts"], color=AQUA, linewidth=1.0, alpha=1 if zoom else 0.35,
              label="instantaneous")
    if not zoom:                    # mean over each 1/60 s AC cycle (133 samples)
        ax_p.plot(t, samples["watts"].rolling(133, center=True).mean(), color=AQUA,
                  linewidth=2, label="mean per AC cycle")
        ax_p.legend(loc="upper right", fontsize=8, frameon=False, labelcolor=INK)
    style(ax_p, "Power (W)")

    # Energy adds up from the first sample shown: each sample is watts x 125 us.
    lines = [("total", samples["watts"].cumsum() * SAMPLE_SECONDS, "-")]
    if summary.get("baseline_watts") is not None:
        above = (samples["watts"] - summary["baseline_watts"]).cumsum() * SAMPLE_SECONDS
        lines.append(("above idle", above, "--"))
    for label, energy, dash in lines:
        ax_e.plot(t, energy, color=VIOLET, linewidth=2, linestyle=dash, label=label)
        ax_e.annotate(f"{energy.iloc[-1]:.2f} J", (t.iloc[-1], energy.iloc[-1]),
                      xytext=(4, 0), textcoords="offset points", va="center",
                      fontsize=8, color=INK)
    ax_e.legend(loc="upper left", fontsize=8, frameon=False, labelcolor=INK)
    style(ax_e, "Energy (J)")
    ax_e.set_xlabel(f"Time since recording started ({'ms' if zoom else 's'})", color=MUTED)

    span = f"first {zoom_cycles} AC cycles" if zoom else "whole recording"
    fig.suptitle(f"{summary['label']} - repetition {summary['repetition']}, "
                 f"call {summary['call']} - {span}\n"
                 f"{summary['workload_seconds']:.3f} s, {summary['mean_watts']:.1f} W mean",
                 color=INK, fontsize=11)
    save(fig, out_path)


def first_cycles(samples, n):
    """Rows covering the first n AC cycles, from a rising voltage zero crossing."""
    v = samples["L1_mV"].to_numpy()
    rising = np.where((v[:-1] < 0) & (v[1:] >= 0))[0]
    if len(rising) <= n:
        return samples
    return samples.iloc[rising[0]:rising[n] + 1]


# ======================================================================
# The run: energy per repetition, temperature before each repetition
# ======================================================================

def plot_energy_per_repetition(run):
    """One panel per label: energy above idle (all calls of a repetition added up)."""
    if not run.measurements_csv.exists():
        return
    df = pd.read_csv(run.measurements_csv)
    df = df[df["repetition"] > 0]
    if df.empty:
        return
    column = ("energy_above_idle_joules" if df["energy_above_idle_joules"].notna().all()
              else "joules")
    per_rep = df.groupby(["label", "repetition"], sort=False)[column].sum().reset_index()
    labels = list(per_rep["label"].unique())
    fig = new_figure(len(labels), height=2.6 * len(labels) + 1)
    for ax, label in zip(fig.axes, labels):
        rows = per_rep[per_rep["label"] == label]
        values = rows[column]
        ax.plot(rows["repetition"], values, color=BLUE, linewidth=2, marker="o", markersize=6)
        spread = f" ± {values.std():.2f}" if len(values) > 1 else ""
        ax.set_title(f"{label}: {values.mean():.2f}{spread} J", color=INK, fontsize=10, loc="left")
        style(ax, "Energy above idle (J)" if column != "joules" else "Energy (J)")
        include_zero(ax, values)
        ax.set_xticks(rows["repetition"])
    fig.axes[-1].set_xlabel("Repetition", color=MUTED)
    fig.suptitle("Energy per repetition", color=INK, fontsize=11)
    save(fig, run.plots_dir / "energy_per_repetition.png")


def plot_temperature(run):
    """Per check: the readings of the last window (min to max, dot = mean) against
    the reference +- spread band, and how long the check took."""
    checks = [json.loads(p.read_text()) for p in sorted(run.checks_dir.glob("*_temperature_rep*.json"))]
    checks = [c for c in checks if c.get("sensor")]
    if not checks:
        return
    reps = [c["repetition"] for c in checks]
    last = [c["windows"][-1] for c in checks]
    fig = new_figure(2, height=5.5)
    ax_t, ax_w = fig.axes

    reference = checks[0]["idle_temperature_c"]
    spread = checks[0]["spread_c"]
    ax_t.axhspan(reference - spread, reference + spread, color=GRID, alpha=0.6, linewidth=0)
    ax_t.axhline(reference, color=MUTED, linewidth=1, linestyle="--")
    ax_t.annotate(f"reference {reference:.1f} ± {spread:g} degC", (0, reference + spread),
                  xycoords=("axes fraction", "data"), xytext=(4, 3),
                  textcoords="offset points", fontsize=8, color=MUTED)
    ax_t.vlines(reps, [w["min_c"] for w in last], [w["max_c"] for w in last],
                color=BLUE, linewidth=2)
    ax_t.plot(reps, [w["mean_c"] for w in last], color=BLUE, linestyle="none",
              marker="o", markersize=6)
    style(ax_t, "CPU temperature (degC)")

    waited = [c["waited_seconds"] for c in checks]
    ax_w.plot(reps, waited, color=BLUE, linewidth=2, marker="o", markersize=6)
    style(ax_w, "Check took (s)")
    include_zero(ax_w, waited)
    ax_w.set_xticks(reps)
    ax_w.set_xlabel("Before repetition (0 = initial idle check)", color=MUTED)
    fig.suptitle("CPU temperature before each repetition", color=INK, fontsize=11)
    save(fig, run.plots_dir / "temperature.png")


# ======================================================================
# Shared look
# ======================================================================

def new_figure(rows, height):
    fig = Figure(figsize=(10, height), facecolor=SURFACE)
    fig.subplots(rows, 1, sharex=True, squeeze=False)
    return fig


def style(ax, ylabel):
    ax.set_facecolor(SURFACE)
    ax.set_ylabel(ylabel, color=MUTED)
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.tick_params(colors=MUTED, labelsize=8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)


def include_zero(ax, values):
    """Show amounts from zero, so small differences do not look large."""
    low, high = min(0, min(values)), max(0, max(values))
    pad = 0.15 * (high - low) or 1
    ax.set_ylim(low - pad if low < 0 else 0, high + pad)
    ax.ticklabel_format(axis="y", useOffset=False)


def save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=120, facecolor=SURFACE)


if __name__ == "__main__":
    plot_run(RunFolder(sys.argv[1]))
