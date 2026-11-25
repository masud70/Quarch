"""Records measurements of one repetition into a run folder."""

import os
from collections import Counter

from .meter import QuarchMeter
from .run_folder import RunFolder
from .samples import SampleParser
from .segment import Segment
from .settings import DEVICE, ENV_BASELINE_WATTS, ENV_DEVICE, ENV_REPETITION, ENV_RUN_DIR
from .temperature import CpuTemperature


class Recorder:
    """Everything needed to record: the meter, the sample parser, the CPU
    temperature, the run folder, and a call counter per label.

        recorder = Recorder(run, repetition=1, baseline_watts=35.0)
        with recorder.segment("fit"):
            ...
        recorder.close()
    """

    def __init__(self, run, repetition, baseline_watts=None, device=DEVICE, save_samples=True):
        self.run = run
        self.repetition = repetition
        self.baseline_watts = baseline_watts
        self.save_samples = save_samples
        self.meter = QuarchMeter(device)
        self.parser = SampleParser()
        self.temperature = CpuTemperature()
        self.calls = Counter()              # label -> calls so far in this repetition

    @classmethod
    def from_environment(cls):
        """The Recorder the runner set up for this process, or None when the file
        was started without the runner."""
        run_dir = os.environ.get(ENV_RUN_DIR)
        if not run_dir:
            return None
        baseline = os.environ.get(ENV_BASELINE_WATTS)
        return cls(RunFolder(run_dir),
                   repetition=int(os.environ[ENV_REPETITION]),
                   baseline_watts=float(baseline) if baseline else None,
                   device=os.environ.get(ENV_DEVICE, DEVICE))

    def segment(self, label):
        """A `with` block that records one measurement of `label`."""
        self.calls[label] += 1
        return Segment(self, label, self.calls[label])

    def close(self):
        self.meter.close()
