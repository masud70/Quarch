"""summary.csv: one row per label, mean and spread over the repetitions."""

import pandas as pd


def summarize(run):
    """Read measurements.csv, write summary.csv, return it (None if nothing recorded).
    Each repetition's calls of a label are added up first, so a label called
    twice per repetition counts as one value per repetition."""
    if not run.measurements_csv.exists():
        return None
    df = pd.read_csv(run.measurements_csv)
    df = df[df["repetition"] > 0]                   # leave out the idle measurement
    if df.empty:
        return None
    per_rep = df.groupby(["label", "repetition"], sort=False).agg(
        calls=("call", "count"),
        seconds=("workload_seconds", "sum"),
        joules=("joules", "sum"),
        above_idle_joules=("energy_above_idle_joules", "sum"),
        mean_watts=("mean_watts", "mean"),
    ).reset_index()
    summary = per_rep.groupby("label", sort=False).agg(
        repetitions=("repetition", "count"),
        calls_per_rep=("calls", "mean"),
        seconds_mean=("seconds", "mean"),
        seconds_std=("seconds", "std"),
        joules_mean=("joules", "mean"),
        joules_std=("joules", "std"),
        above_idle_joules_mean=("above_idle_joules", "mean"),
        above_idle_joules_std=("above_idle_joules", "std"),
        above_idle_joules_min=("above_idle_joules", "min"),
        above_idle_joules_max=("above_idle_joules", "max"),
        mean_watts=("mean_watts", "mean"),
    ).reset_index().round(4)
    summary.to_csv(run.summary_csv, index=False)
    return summary
