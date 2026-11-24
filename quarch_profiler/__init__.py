"""Wall energy (Quarch) of a function or a block of code, with every sample kept.

    from quarch_profiler import QuarchProfiler

    profiler = QuarchProfiler(save_dir="profiles")
    profiler.measure_idle(30)                       # optional: subtract idle power

    # 1. a function - every call is recorded
    @profiler.measure("fit")
    def train(X, y):
        return clf.fit(X, y)

    train(X, y)
    m = train.last                                  # Measurement of that call

    # 2. a block of code
    with profiler.segment("predict") as seg:
        clf.predict(X_test)
    m = seg.result

    m.joules, m.energy_above_idle_joules, m.mean_watts, m.peak_watts, ...
    m.samples                                       # DataFrame, one row per 125 us sample

QIS is started if it is not running; close Quarch Power Studio first (it runs its
own QIS). Recordings cannot nest: the meter has a single stream.

Files (one class each):
    profiler.py     QuarchProfiler    - the object you use
    decorator.py    MeasuredFunction  - a function measured by @profiler.measure
    segment.py      Segment           - a block measured by `with profiler.segment()`
    measurement.py  Measurement, MeasurementLog - results, saving, to_frame
    meter.py        QuarchMeter       - connect, start/stop a recording (quarchpy)
    samples.py      SampleParser      - raw text -> DataFrame of samples with watts
    temperature.py  CpuTemperature    - CPU package temperature
    settings.py     device name, sample rate, stream columns
"""

from .decorator import MeasuredFunction
from .measurement import Measurement, MeasurementLog
from .meter import QuarchMeter
from .profiler import QuarchProfiler
from .samples import SampleParser
from .segment import Segment
from .temperature import CpuTemperature

__all__ = [
    "QuarchProfiler",
    "QuarchMeter",
    "Measurement",
    "MeasurementLog",
    "MeasuredFunction",
    "Segment",
    "SampleParser",
    "CpuTemperature",
]
