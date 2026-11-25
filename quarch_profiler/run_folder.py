"""One folder per run, holding every report, measurement and plot of that run."""

import csv
import json
import platform
import re
import sys
from datetime import datetime
from pathlib import Path


class RunFolder:
    """runs/<date>_<time>_<file name>/

        run_info.json       what was run, where, with which settings
        report.txt          every check and measurement, readable, in order
        measurements.csv    one row per measurement
        summary.csv         one row per label: mean / std over the repetitions
        checks/             processes, CPU and temperature reports (JSON)
        measurements/<label>/rep01_call01_summary.json (+ _samples.csv)
        plots/              graphs
    """

    def __init__(self, path):
        """Open an existing run folder (the runner creates it with create())."""
        self.path = Path(path)
        self.checks_dir = self.path / "checks"
        self.measurements_dir = self.path / "measurements"
        self.plots_dir = self.path / "plots"
        self.report_file = self.path / "report.txt"
        self.info_file = self.path / "run_info.json"
        self.measurements_csv = self.path / "measurements.csv"
        self.summary_csv = self.path / "summary.csv"

    @classmethod
    def create(cls, root, name):
        """Make runs/<date>_<time>_<name>/ (with _2, _3, ... if it already exists)."""
        base = Path(root) / f"{datetime.now():%Y%m%d_%H%M%S}_{cls._safe(name)}"
        path, n = base, 1
        while path.exists():
            n += 1
            path = base.with_name(f"{base.name}_{n}")
        run = cls(path.resolve())
        for folder in (run.checks_dir, run.measurements_dir, run.plots_dir):
            folder.mkdir(parents=True)
        run.update_info(created=datetime.now().isoformat(timespec="seconds"),
                        host=platform.node(), python=sys.version.split()[0])
        return run

    def __str__(self):
        return str(self.path)

    # ---------------------------------------------------------------- writing

    def update_info(self, **fields):
        """Add fields to run_info.json."""
        info = json.loads(self.info_file.read_text()) if self.info_file.exists() else {}
        info.update(fields)
        self.info_file.write_text(json.dumps(info, indent=2, default=str))

    def log(self, text):
        """Print text and append it to report.txt."""
        print(text, flush=True)
        with self.report_file.open("a") as f:
            f.write(text + "\n")

    def save_check(self, report):
        """Save a CheckReport as checks/<time>_<name>.json and add it to report.txt."""
        stamp = datetime.fromisoformat(report.started_at).strftime("%H%M%S")
        path = self.checks_dir / f"{stamp}_{report.name}.json"
        path.write_text(json.dumps(report.to_dict(), indent=2, default=str))
        self.log(report.text + "\n")

    def save_measurement(self, m, save_samples=True):
        """Save a Measurement to measurements/<label>/, add a row to measurements.csv
        and a line to report.txt."""
        m.save(self.measurements_dir / self._safe(m.label), include_samples=save_samples)
        row = m.summary()
        row["ports"] = "+".join(row["ports"])
        new_file = not self.measurements_csv.exists()
        with self.measurements_csv.open("a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(row))
            if new_file:
                writer.writeheader()
            writer.writerow(row)
        above = m.energy_above_idle_joules
        self.log(f"[rep {m.repetition}] {m.label} #{m.call}: {m.workload_seconds:.3f} s, "
                 f"{m.joules:.2f} J total"
                 + (f", {above:.2f} J above idle" if above is not None else "")
                 + f", {m.mean_watts:.1f} W mean")

    @staticmethod
    def _safe(name):
        return re.sub(r"[^\w.-]+", "_", str(name))
