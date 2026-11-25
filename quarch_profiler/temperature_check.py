"""Temperature check: read the CPU temperature for a while and wait until it is cool."""

import statistics
import time
from datetime import datetime

from .report import CheckReport
from .settings import TEMP_CHECK_INTERVAL, TEMP_CHECK_SECONDS, TEMP_LIMIT_C, TEMP_WAIT_TIMEOUT


class TemperatureCheck:
    """Reads the CPU temperature every `interval` seconds for `seconds` (one window).
    With wait=True, if any reading in the window is above `limit_c`, it reads
    another window, until a whole window is cool or `timeout` seconds have passed.

        report = TemperatureCheck(CpuTemperature()).run(seconds=30, interval=1)
        report.passed        # True = cool, False = still hot, None = no sensor
    """

    def __init__(self, temperature):
        self.temperature = temperature

    def run(self, seconds=TEMP_CHECK_SECONDS, interval=TEMP_CHECK_INTERVAL,
            limit_c=TEMP_LIMIT_C, wait=True, timeout=TEMP_WAIT_TIMEOUT):
        started_at = datetime.now().isoformat(timespec="seconds")
        if not self.temperature.available:
            return CheckReport("temperature", passed=None,
                               data={"sensor": None},
                               lines=["no x86_pkg_temp sensor - temperature not checked"],
                               started_at=started_at)

        t_start = time.monotonic()
        windows = []
        while True:
            readings = self._read_window(seconds, interval)
            window = self._summarize(readings, limit_c)
            windows.append(window)
            print(f"[temperature] window {len(windows)}: min {window['min_c']:.1f}, "
                  f"mean {window['mean_c']:.1f}, max {window['max_c']:.1f} degC "
                  f"-> {'cool' if window['cool'] else f'above {limit_c} degC'}", flush=True)
            if window["cool"] or not wait:
                break
            if time.monotonic() - t_start > timeout:
                break

        last = windows[-1]
        waited = time.monotonic() - t_start
        data = {
            "sensor": self.temperature.zone,
            "seconds": seconds,
            "interval": interval,
            "limit_c": limit_c,
            "wait": wait,
            "timeout": timeout,
            "waited_seconds": waited,
            "n_windows": len(windows),
            "cool": last["cool"],
            "final_window": last,
            "windows": windows,
        }
        if last["cool"]:
            verdict = f"cool: every reading <= {limit_c} degC"
        elif wait:
            verdict = f"WARNING: still above {limit_c} degC after waiting {waited:.0f} s"
        else:
            verdict = f"WARNING: above {limit_c} degC"
        lines = [
            f"CPU temperature every {interval} s for {seconds} s "
            f"(limit {limit_c} degC, {len(windows)} window(s), {waited:.0f} s in total)",
            f"last window: start {last['start_c']:.1f}, end {last['end_c']:.1f}, "
            f"min {last['min_c']:.1f}, mean {last['mean_c']:.1f}, max {last['max_c']:.1f} degC, "
            f"trend {last['trend_c']:+.1f} degC",
            verdict,
        ]
        return CheckReport("temperature", passed=last["cool"], data=data, lines=lines,
                           started_at=started_at)

    def _read_window(self, seconds, interval):
        """[(seconds since window start, degC), ...], one reading every `interval`."""
        n = max(1, round(seconds / interval))
        t0 = time.monotonic()
        readings = []
        for i in range(n):
            readings.append((time.monotonic() - t0, self.temperature.read()))
            if i < n - 1:
                time.sleep(interval)
        return readings

    @staticmethod
    def _summarize(readings, limit_c):
        temps = [t for _, t in readings]
        return {
            "n_readings": len(temps),
            "start_c": temps[0],
            "end_c": temps[-1],
            "min_c": min(temps),
            "mean_c": statistics.fmean(temps),
            "max_c": max(temps),
            "trend_c": temps[-1] - temps[0],
            "cool": max(temps) <= limit_c,
            "readings": [{"t_s": round(t, 3), "temp_c": c} for t, c in readings],
        }
