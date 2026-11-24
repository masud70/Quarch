"""QuarchProfiler: the one object you create to measure functions and code blocks."""

import time

from .decorator import MeasuredFunction
from .meter import QuarchMeter
from .samples import SampleParser
from .segment import Segment
from .settings import DEVICE
from .temperature import CpuTemperature


class QuarchProfiler:
    """Measure the wall energy of functions and blocks of code.

        profiler = QuarchProfiler(save_dir="profiles")
        profiler.measure_idle(30)            # optional: subtract idle power from now on

        @profiler.measure("fit")
        def train(X, y): ...

        with profiler.segment("predict") as seg:
            clf.predict(X)

    Defaults given here (baseline_watts, save_dir, keep_samples) apply to every
    measurement; measure() and segment() can override them one at a time.
    """

    def __init__(self, device=DEVICE, *, baseline_watts=None, save_dir=None,
                 keep_samples=True):
        self.meter = QuarchMeter(device)
        self.parser = SampleParser()
        self.temperature = CpuTemperature()
        self.baseline_watts = baseline_watts
        self.save_dir = save_dir
        self.keep_samples = keep_samples

    # ------------------------------------------------------------ measuring

    def segment(self, label="segment", **options):
        """A `with` block to measure. Options: baseline_watts, save_dir,
        keep_samples, extra (any dict stored with the result)."""
        settings = {"baseline_watts": self.baseline_watts,
                    "save_dir": self.save_dir,
                    "keep_samples": self.keep_samples,
                    **options}
        return Segment(self.meter, self.parser, self.temperature, label, **settings)

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
            with self.segment("idle", baseline_watts=None, save_dir=None,
                              keep_samples=False) as seg:
                time.sleep(seconds)
            total += seg.result.mean_watts
        self.baseline_watts = total / repetitions
        return self.baseline_watts

    # ----------------------------------------------------------- connection

    def close(self):
        self.meter.close()

    def __enter__(self):
        self.meter.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
