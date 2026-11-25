"""One recording: wall power while a `with` block runs."""

import time
from datetime import datetime

from .measurement import Measurement


class Segment:
    """Records while the `with` block runs, then saves the Measurement to the run
    folder. Made by Recorder.segment(). The result is in .result (samples are
    saved to disk and freed from memory).

    If the block raises, the recording is stopped and thrown away, and the
    exception propagates (.result stays None).
    """

    def __init__(self, recorder, label, call):
        self.recorder = recorder
        self.label = label
        self.call = call
        self.result = None

    def __enter__(self):
        rec = self.recorder
        self._temp_start = rec.temperature.read()
        rec.meter.start_recording()
        self._started_at = datetime.now().isoformat(timespec="microseconds")
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        rec = self.recorder
        workload_seconds = time.perf_counter() - self._t0
        temp_end = rec.temperature.read()   # inside the window, before the readout heats the CPU

        if exc_type is not None:
            rec.meter.abort_recording()
            return False                    # let the block's exception propagate

        raw = rec.meter.stop_recording()
        self.result = Measurement.from_samples(
            self.label, rec.parser.parse(raw),
            repetition=rec.repetition,
            call=self.call,
            started_at=self._started_at,
            workload_seconds=workload_seconds,
            baseline_watts=rec.baseline_watts,
            temp_start=self._temp_start,
            temp_end=temp_end,
            device=rec.meter.device,
            ports=rec.parser.ports,
        )
        rec.run.save_measurement(self.result, save_samples=rec.save_samples)
        self.result.samples = None          # on disk now; free the memory
        return False
