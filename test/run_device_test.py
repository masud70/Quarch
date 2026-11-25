"""Quick test of quarch_profiler on the real meter: python3 test/run_device_test.py"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quarch_profiler import QuarchMeter, QuarchProfiler  # noqa: E402


def busy(seconds):
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        pass


print("devices:", QuarchMeter.list_devices())

profiler = QuarchProfiler(name="device_test")   # checks run before the first measurement
print(f"idle: {profiler.measure_idle(10):.2f} W")


@profiler.measure("busy")
def work(seconds):
    busy(seconds)


work(2)
work(6)
e1, e3 = (m.energy_above_idle_joules for m in work.measurements)
print(f"busy 2 s: {e1:.2f} J, 6 s: {e3:.2f} J, ratio {e3 / e1:.2f} (expect ~3)")

with profiler.segment("sleep") as seg:
    time.sleep(2)
m = seg.result
print(f"sleep 2 s: {m.n_samples} samples, {m.mean_watts:.1f} W, "
      f"{m.energy_above_idle_joules:.2f} J above idle (expect ~0)")

print("reports:", profiler.run.path)
