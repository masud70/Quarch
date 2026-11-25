"""The runner: checks the machine, then runs your file n times and records it."""

import os
import subprocess
import sys
import time
from pathlib import Path

from .cpu_check import CpuUsageCheck
from .plots import plot_run
from .process_check import ProcessCheck
from .recorder import Recorder
from .run_folder import RunFolder
from .settings import (DEVICE, ENV_BASELINE_WATTS, ENV_DEVICE, ENV_REPETITION, ENV_RUN_DIR,
                       IDLE_SECONDS, PORTS, RUNS_DIR)
from .summary import summarize
from .temperature import CpuTemperature
from .temperature_check import TemperatureCheck

PACKAGE_PARENT = Path(__file__).resolve().parent.parent     # so your file can import us


class Runner:
    """Runs `script` `repeat` times and records every @measure / segment in it.

    1. once:   process check (you choose what to close), CPU usage report,
               idle temperature (wait until stable = the reference), idle power
    2. each repetition: wait until the temperature is stable and near the
               reference, then run the script in a fresh Python process
    3. at the end: summary.csv and plots
    """

    def __init__(self, script, repeat=1, idle_seconds=IDLE_SECONDS, script_args=(),
                 device=DEVICE):
        self.script = Path(script).resolve()
        self.repeat = repeat
        self.idle_seconds = idle_seconds
        self.script_args = list(script_args)
        self.device = device
        self.temperature_check = TemperatureCheck(CpuTemperature())
        self.reference_c = None             # idle temperature, set by the first check
        self.baseline_watts = None          # idle power, set once
        self.run = None

    def start(self):
        if not self.script.exists():
            raise SystemExit(f"no such file: {self.script}")
        self.run = RunFolder.create(RUNS_DIR, self.script.stem)
        self.run.update_info(script=str(self.script), script_args=self.script_args,
                             repeat=self.repeat, idle_seconds=self.idle_seconds,
                             device=self.device, ports=PORTS)
        self.run.log(f"[runner] {self.script.name} x {self.repeat} -> {self.run}")
        try:
            self.prepare()
            for repetition in range(1, self.repeat + 1):
                self.wait_for_idle_temperature(repetition)
                if not self.run_script(repetition):
                    break
        finally:
            self.finish()

    # ---------------------------------------------------------------- steps

    def prepare(self):
        """Once: close processes, report CPU usage, idle temperature and power."""
        self.run.save_check(ProcessCheck().run())
        self.run.save_check(CpuUsageCheck().run())
        self.wait_for_idle_temperature(repetition=0)    # sets the reference
        self.measure_idle_power()

    def wait_for_idle_temperature(self, repetition):
        """Wait until the CPU temperature is stable (and, after the first check,
        near the reference). Raises if it does not settle."""
        report = self.temperature_check.run(reference_c=self.reference_c,
                                            seconds=self.idle_seconds)
        report.name = f"temperature_rep{repetition:02d}"
        report.data["repetition"] = repetition
        self.run.save_check(report)
        if report.passed is False:
            raise RuntimeError(f"CPU temperature did not settle before repetition "
                               f"{repetition} - stopping (see {self.run.report_file})")
        if self.reference_c is None and report.passed:
            self.reference_c = report.data["idle_temperature_c"]
            self.run.update_info(idle_temperature_c=self.reference_c)

    def measure_idle_power(self):
        """Once: mean wall power while idle, subtracted from every measurement."""
        recorder = Recorder(self.run, repetition=0, device=self.device, save_samples=False)
        try:
            with recorder.segment("idle") as seg:
                time.sleep(self.idle_seconds)
        finally:
            recorder.close()                # free the meter for the script's process
        self.baseline_watts = seg.result.mean_watts
        self.run.update_info(baseline_watts=self.baseline_watts)
        self.run.log(f"[runner] idle power {self.baseline_watts:.3f} W "
                     f"- subtracted from every measurement\n")

    def run_script(self, repetition):
        """Run the script once in a new Python process. Returns True if it succeeded."""
        env = dict(os.environ)
        env.update({
            ENV_RUN_DIR: str(self.run.path),
            ENV_REPETITION: str(repetition),
            ENV_BASELINE_WATTS: str(self.baseline_watts),
            ENV_DEVICE: self.device,
            "PYTHONPATH": os.pathsep.join(filter(None, [str(PACKAGE_PARENT),
                                                        env.get("PYTHONPATH")])),
        })
        self.run.log(f"[runner] repetition {repetition}/{self.repeat}: {self.script.name}")
        result = subprocess.run([sys.executable, str(self.script), *self.script_args], env=env)
        if result.returncode != 0:
            self.run.log(f"[runner] the script failed (exit code {result.returncode}) "
                         f"- stopping")
            self.run.update_info(failed_repetition=repetition)
            return False
        return True

    def finish(self):
        """Summary and plots of whatever was recorded."""
        summary = summarize(self.run)
        if summary is not None:
            self.run.log("[runner] summary (mean over repetitions):\n"
                         + summary.to_string(index=False) + "\n")
        plot_run(self.run)
        self.run.log(f"[runner] done - everything is in {self.run}")
