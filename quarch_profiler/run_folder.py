"""One folder per run, holding every report and measurement of that run."""

import csv
import json
import platform
import re
import sys
from datetime import datetime
from pathlib import Path

from .settings import RUNS_DIR


class RunFolder:
    """runs/<date_time>_<name>/

        run_info.json       when, where and with what the run was made
        report.txt          every check and measurement, human-readable, in order
        measurements.csv    one row per measurement
        checks/             <time>_cpu.json, <time>_temperature.json, <time>_processes.json
        measurements/       <time>_<label>_summary.json (+ _samples.csv)
    """

    def __init__(self, root=RUNS_DIR, name=None):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder = f"{stamp}_{self._safe(name)}" if name else stamp
        self.path = Path(root) / folder
        self.checks_dir = self.path / "checks"
        self.measurements_dir = self.path / "measurements"
        self.checks_dir.mkdir(parents=True, exist_ok=False)
        self.measurements_dir.mkdir()
        self.report_file = self.path / "report.txt"
        self.measurements_csv = self.path / "measurements.csv"

    def __str__(self):
        return str(self.path)

    # ---------------------------------------------------------------- writing

    def save_info(self, info):
        info = {
            "created": datetime.now().isoformat(timespec="seconds"),
            "host": platform.node(),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            **info,
        }
        self._write_json(self.path / "run_info.json", info)

    def log(self, text):
        """Print text and append it to report.txt."""
        print(text, flush=True)
        with self.report_file.open("a") as f:
            f.write(text + "\n")

    def save_check(self, report):
        """Save a CheckReport as checks/<time>_<name>.json and add it to report.txt."""
        stamp = datetime.fromisoformat(report.started_at).strftime("%H%M%S")
        self._write_json(self.checks_dir / f"{stamp}_{report.name}.json", report.to_dict())
        self.log(report.text + "\n")

    def save_measurement(self, measurement, save_samples=True):
        """Save one Measurement's files, add a row to measurements.csv and a line
        to report.txt."""
        measurement.save(self.measurements_dir, include_samples=save_samples)
        row = measurement.summary()
        row["extra"] = json.dumps(row["extra"], default=str)
        row["ports"] = "+".join(row["ports"])
        new_file = not self.measurements_csv.exists()
        with self.measurements_csv.open("a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(row))
            if new_file:
                writer.writeheader()
            writer.writerow(row)
        above = measurement.energy_above_idle_joules
        self.log(f"[measurement] {measurement.label}: {measurement.workload_seconds:.3f} s, "
                 f"{measurement.joules:.2f} J total"
                 + (f", {above:.2f} J above idle" if above is not None else "")
                 + f", {measurement.mean_watts:.1f} W mean")

    # --------------------------------------------------------------- helpers

    @staticmethod
    def _safe(name):
        return re.sub(r"[^\w.-]+", "_", str(name))

    @staticmethod
    def _write_json(path, data):
        path.write_text(json.dumps(data, indent=2, default=str))
