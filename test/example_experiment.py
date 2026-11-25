"""Example experiment: python3 -m quarch_profiler test/example_experiment.py -n 3"""

import time

from quarch_profiler import measure, segment


@measure("busy_2s")
def busy(seconds=2):
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        pass


busy()

with segment("sleep_2s"):
    time.sleep(2)
