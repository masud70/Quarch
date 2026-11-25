"""The result of one recording."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

from .settings import SAMPLE_SECONDS


@dataclass
class Measurement:
    """Summary numbers of one recording, plus (until saved) every sample."""

    label: str
    repetition: int                     # 0 = the idle measurement before the repetitions
    call: int                           # 1 for the first call of this label in a repetition
    started_at: str                     # ISO time the recording started
    workload_seconds: float             # timed by perf_counter around the code
    window_seconds: float               # length of the recording (from the sample count)
    n_samples: int
    joules: float                       # total wall energy in the window
    mean_watts: float
    peak_watts: float
    min_watts: float
    std_watts: float
    baseline_watts: float | None        # idle power, if known
    baseline_joules: float | None       # idle power x window
    energy_above_idle_joules: float | None
    cpu_temp_start_c: float
    cpu_temp_end_c: float               # read inside the window, before the meter readout
    device: str = ""
    ports: tuple = ()                   # meter ports counted in watts / joules
    samples: pd.DataFrame | None = field(default=None, repr=False)

    @classmethod
    def from_samples(cls, label, samples, *, repetition, call, started_at, workload_seconds,
                     baseline_watts, temp_start, temp_end, device, ports):
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
            repetition=repetition,
            call=call,
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
            ports=tuple(ports),
            samples=samples,
        )

    @property
    def name(self):
        """File name stem, e.g. rep01_call01."""
        return f"rep{self.repetition:02d}_call{self.call:02d}"

    def summary(self):
        """Everything except the samples, as a flat dict."""
        d = asdict(self)
        d.pop("samples")
        return d

    def save(self, out_dir, include_samples=True):
        """Write <name>_summary.json and, if include_samples, <name>_samples.csv."""
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        if include_samples and self.samples is not None:
            self.samples.to_csv(out_dir / f"{self.name}_samples.csv", index=False)
        (out_dir / f"{self.name}_summary.json").write_text(
            json.dumps(self.summary(), indent=2, default=str))
