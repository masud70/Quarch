"""Wall energy (Quarch) of a function or a block of code, with every sample kept.

    from quarch_profiler import QuarchProfiler

    profiler = QuarchProfiler(name="rf_mnist")      # reports -> runs/<date_time>_rf_mnist/
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

    # checks: run automatically before the first measurement, or any time
    profiler.check_processes()                      # list, close the ones you choose
    profiler.check_cpu(seconds=10, interval=1)
    profiler.check_temperature(seconds=30, interval=1)   # waits until cool

QIS is started if it is not running; close Quarch Power Studio first (it runs its
own QIS). Recordings cannot nest: the meter has a single stream.

Files (one class each):
    profiler.py           QuarchProfiler    - the object you use
    decorator.py          MeasuredFunction  - a function measured by @profiler.measure
    segment.py            Segment           - a block measured by `with profiler.segment()`
    measurement.py        Measurement, MeasurementLog - results
    run_folder.py         RunFolder         - one folder with every report of a run
    cpu_check.py          CpuUsageCheck     - CPU usage
    temperature_check.py  TemperatureCheck  - temperature over time, wait until cool
    process_check.py      ProcessCheck      - running processes, close chosen ones
    report.py             CheckReport       - the result of one check
    meter.py              QuarchMeter       - connect, start/stop a recording (quarchpy)
    samples.py            SampleParser      - raw text -> DataFrame of samples with watts
    temperature.py        CpuTemperature    - reads the CPU package temperature
    settings.py           device, ports, run folder and check settings
"""

from .cpu_check import CpuUsageCheck
from .decorator import MeasuredFunction
from .measurement import Measurement, MeasurementLog
from .meter import QuarchMeter
from .process_check import ProcessCheck
from .profiler import QuarchProfiler
from .report import CheckReport
from .run_folder import RunFolder
from .samples import SampleParser
from .segment import Segment
from .temperature import CpuTemperature
from .temperature_check import TemperatureCheck

__all__ = [
    "QuarchProfiler",
    "QuarchMeter",
    "Measurement",
    "MeasurementLog",
    "MeasuredFunction",
    "Segment",
    "RunFolder",
    "CheckReport",
    "CpuUsageCheck",
    "TemperatureCheck",
    "ProcessCheck",
    "SampleParser",
    "CpuTemperature",
]
