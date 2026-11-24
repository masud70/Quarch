"""The result of one recording, and a list of results."""

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

from .settings import SAMPLE_SECONDS


@dataclass
class Measurement:
    """Summary numbers of one recording, plus (optionally) every sample."""

    label: str
    started_at: str                     # ISO time the recording started
    workload_seconds: float             # timed by perf_counter around the code
    window_seconds: float               # length of the recording (from the sample count)
    n_samples: int
    joules: float                       # total wall energy in the window
    mean_watts: float
    peak_watts: float
    min_watts: float
    std_watts: float
    baseline_watts: float | None        # idle power, if given
    baseline_joules: float | None       # idle power x window
    energy_above_idle_joules: float | None
    cpu_temp_start_c: float
    cpu_temp_end_c: float               # read inside the window, before the meter readout
    device: str = ""
    extra: dict = field(default_factory=dict)       # e.g. function name, call number
    samples: pd.DataFrame | None = field(default=None, repr=False)

    @classmethod
    def from_samples(cls, label, samples, *, started_at, workload_seconds, baseline_watts,
                     temp_start, temp_end, device, keep_samples=True, extra=None):
        """Build a Measurement from the DataFrame made by SampleParser."""
        watts = samples["watts"].to_numpy()
        if len(watts) == 0:
            raise RuntimeError(f"[{label}] the meter returned no samples")
        # Every sample covers 125 us, so energy = sum of watts x 125 us.
        joules = float(watts.sum() * SAMPLE_SECONDS)
        window = len(watts) * SAMPLE_SECONDS
        baseline_joules = None if baseline_watts is None else baseline_watts * window
        return cls(
            label=label,
            started_at=started_at,
            workload_seconds=workload_seconds,
            window_seconds=window,
            n_samples=len(watts),
            joules=joules,
            mean_watts=joules / window,
            peak_watts=float(watts.max()),
            min_watts=float(watts.min()),
            std_watts=float(watts.std()),
            baseline_watts=baseline_watts,
            baseline_joules=baseline_joules,
            energy_above_idle_joules=None if baseline_joules is None else joules - baseline_joules,
            cpu_temp_start_c=temp_start,
            cpu_temp_end_c=temp_end,
            device=device,
            extra=dict(extra or {}),
            samples=samples if keep_samples else None,
        )

    def summary(self):
        """Everything except the samples, as a flat dict."""
        d = asdict(self)
        d.pop("samples")
        return d

    def save(self, out_dir):
        """Write <time>_<label>_summary.json and, if samples were kept, _samples.csv.
        Returns the summary path."""
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = (datetime.fromisoformat(self.started_at).strftime("%Y%m%d_%H%M%S_%f")
                + "_" + re.sub(r"[^\w.-]+", "_", self.label))
        if self.samples is not None:
            self.samples.to_csv(out_dir / f"{stem}_samples.csv", index=False)
        path = out_dir / f"{stem}_summary.json"
        path.write_text(json.dumps(self.summary(), indent=2, default=str))
        return path


class MeasurementLog(list):
    """A list of Measurements, e.g. every call of a measured function."""

    @property
    def last(self):
        """The newest Measurement, None if empty."""
        return self[-1] if self else None

    def to_frame(self):
        """One row per Measurement (without samples)."""
        return pd.DataFrame([m.summary() for m in self])
