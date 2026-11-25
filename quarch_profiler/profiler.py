"""QuarchProfiler: the one object you create to measure functions and code blocks."""

import time

from .cpu_check import CpuUsageCheck
from .decorator import MeasuredFunction
from .meter import QuarchMeter
from .process_check import ProcessCheck
from .run_folder import RunFolder
from .samples import SampleParser
from .segment import Segment
from .settings import (CONNECT_TIMEOUT, CPU_CHECK_INTERVAL, CPU_CHECK_SECONDS, DEVICE, RUNS_DIR,
                       TEMP_CHECK_INTERVAL, TEMP_CHECK_SECONDS, TEMP_LIMIT_C,
                       TEMP_WAIT_TIMEOUT)
from .temperature import CpuTemperature
from .temperature_check import TemperatureCheck


class QuarchProfiler:
    """Measure the wall energy of functions and blocks of code.

        profiler = QuarchProfiler(name="rf_mnist")   # reports go to runs/<date_time>_rf_mnist/
        profiler.measure_idle(30)                    # optional: subtract idle power from now on

        @profiler.measure("fit")
        def train(X, y): ...

        with profiler.segment("predict") as seg:
            clf.predict(X)

    Before the first measurement, the checks run once (prechecks=True):
    processes (you choose what to close), CPU usage, then temperature (waits
    until cool). Each check can also be run any time: check_processes(),
    check_cpu(), check_temperature().

    Defaults given here (baseline_watts, keep_samples, save_samples) apply to
    every measurement; measure() and segment() can override them one at a time.
    """

    def __init__(self, device=DEVICE, *, name=None, runs_dir=RUNS_DIR, prechecks=True,
                 baseline_watts=None, keep_samples=True, save_samples=True,
                 connect_timeout=CONNECT_TIMEOUT):
        self.meter = QuarchMeter(device, connect_timeout=connect_timeout)
        self.parser = SampleParser()
        self.temperature = CpuTemperature()
        self.cpu_check = CpuUsageCheck()
        self.temperature_check = TemperatureCheck(self.temperature)
        self.process_check = ProcessCheck()
        self.prechecks = prechecks
        self.prechecks_done = False
        self.baseline_watts = baseline_watts
        self.keep_samples = keep_samples
        self.save_samples = save_samples

        self.run = RunFolder(runs_dir, name)
        self.run.save_info({"name": name, "device": device, "connect_timeout": connect_timeout,
                            "ports": self.parser.ports,
                            "prechecks": prechecks, "baseline_watts": baseline_watts,
                            "temperature_sensor": self.temperature.zone})
        self.run.log(f"[quarch_profiler] run folder: {self.run}")

    # ------------------------------------------------------------- measuring

    def segment(self, label="segment", **options):
        """A `with` block to measure. Options: baseline_watts, keep_samples,
        save_samples, extra (any dict stored with the result)."""
        self._run_prechecks_once()
        settings = {"baseline_watts": self.baseline_watts,
                    "keep_samples": self.keep_samples,
                    "save_samples": self.save_samples,
                    **options}
        return Segment(self.meter, self.parser, self.temperature, self.run, label, **settings)

    def measure(self, label=None, *, record_args=False, **options):
        """Decorator for a function, with or without arguments:

            @profiler.measure
            @profiler.measure("fit", record_args=True, keep_samples=False)

        record_args=True stores repr() of each call's arguments with its result.
        Other options: as for segment().
        """
        if callable(label):                 # used bare: @profiler.measure
            return MeasuredFunction(label, self)

        def decorate(fn):
            return MeasuredFunction(fn, self, label, record_args, **options)

        return decorate

    def measure_idle(self, seconds=30, repetitions=1):
        """Mean wall power while the machine does nothing: `repetitions` recordings of
        `seconds` each. Also used as baseline_watts for every later measurement."""
        total = 0.0
        for _ in range(repetitions):
            with self.segment("idle", baseline_watts=None, keep_samples=False,
                              save_samples=False) as seg:
                time.sleep(seconds)
            total += seg.result.mean_watts
        self.baseline_watts = total / repetitions
        self.run.log(f"[idle] baseline {self.baseline_watts:.3f} W "
                     f"({repetitions} x {seconds} s) - subtracted from now on")
        return self.baseline_watts

    # ---------------------------------------------------------------- checks

    def run_prechecks(self):
        """Processes (you choose what to close), then CPU usage, then temperature
        (waits until cool). Raises RuntimeError if it does not cool down."""
        self.run.log("[quarch_profiler] checks before measuring")
        self.check_processes()
        self.check_cpu()
        report = self.check_temperature(wait=True)
        self.prechecks_done = report.passed is not False     # hot: check again next time
        if report.passed is False:
            raise RuntimeError(f"CPU did not cool below {report.data['limit_c']} degC within "
                               f"{report.data['timeout']} s - not measuring "
                               f"(see {self.run.report_file})")

    def check_processes(self, interactive=None):
        """List running processes; in a terminal, close the ones you choose."""
        return self._save(self.process_check.run(interactive=interactive))

    def check_cpu(self, seconds=CPU_CHECK_SECONDS, interval=CPU_CHECK_INTERVAL):
        """CPU usage every `interval` s for `seconds`, per core and busiest processes."""
        return self._save(self.cpu_check.run(seconds=seconds, interval=interval))

    def check_temperature(self, seconds=TEMP_CHECK_SECONDS, interval=TEMP_CHECK_INTERVAL,
                          limit_c=TEMP_LIMIT_C, wait=True, timeout=TEMP_WAIT_TIMEOUT):
        """CPU temperature every `interval` s for `seconds`; with wait=True, repeat
        until a whole window is at or below `limit_c` (or `timeout` s pass)."""
        return self._save(self.temperature_check.run(
            seconds=seconds, interval=interval, limit_c=limit_c, wait=wait, timeout=timeout))

    def _run_prechecks_once(self):
        if self.prechecks and not self.prechecks_done:
            self.run_prechecks()

    def _save(self, report):
        self.run.save_check(report)
        return report

    # ------------------------------------------------------------ connection

    def close(self):
        self.meter.close()

    def __enter__(self):
        self.meter.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
