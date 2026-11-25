"""Measuring a block of code: `with profiler.segment(...)`."""

import time
from datetime import datetime

from .measurement import Measurement


class Segment:
    """Records wall power while the `with` block runs. The result is in .result.
    Made by QuarchProfiler.segment(); you normally do not create it yourself.

        with profiler.segment("predict") as seg:
            clf.predict(X)
        seg.result.joules

    The result is saved to the run folder (summary, and samples if save_samples).
    If the block raises, the recording is stopped and thrown away, and the
    exception propagates (.result stays None).
    """

    def __init__(self, meter, parser, temperature, run, label="segment", *,
                 baseline_watts=None, keep_samples=True, save_samples=True, extra=None):
        self.meter = meter
        self.parser = parser
        self.temperature = temperature
        self.run = run
        self.label = label
        self.baseline_watts = baseline_watts
        self.keep_samples = keep_samples
        self.save_samples = save_samples
        self.extra = extra
        self.result = None

    def __enter__(self):
        self._temp_start = self.temperature.read()
        self.meter.start_recording()
        self._started_at = datetime.now().isoformat(timespec="microseconds")
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        workload_seconds = time.perf_counter() - self._t0
        temp_end = self.temperature.read()  # inside the window, before the readout heats the CPU

        if exc_type is not None:
            self.meter.abort_recording()
            return False                    # let the block's exception propagate

        raw = self.meter.stop_recording()
        self.result = Measurement.from_samples(
            self.label, self.parser.parse(raw),
            started_at=self._started_at,
            workload_seconds=workload_seconds,
            baseline_watts=self.baseline_watts,
            temp_start=self._temp_start,
            temp_end=temp_end,
            device=self.meter.device,
            ports=self.parser.ports,
            extra=self.extra,
        )
        self.run.save_measurement(self.result, save_samples=self.save_samples)
        if not self.keep_samples:
            self.result.samples = None      # saved to disk (if asked), freed from memory
        return False
