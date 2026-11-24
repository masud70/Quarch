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

    If the block raises, the recording is stopped and thrown away, and the
    exception propagates (.result stays None).
    """

    def __init__(self, meter, parser, temperature, label="segment", *, baseline_watts=None,
                 save_dir=None, keep_samples=True, extra=None):
        self.meter = meter
        self.parser = parser
        self.temperature = temperature
        self.label = label
        self.baseline_watts = baseline_watts
        self.save_dir = save_dir
        self.keep_samples = keep_samples
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
            keep_samples=self.keep_samples,
            extra=self.extra,
        )
        if self.save_dir is not None:
            self.result.save(self.save_dir)
        return False
