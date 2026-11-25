"""Temperature check: wait until the CPU temperature is stable and near idle."""

import statistics
import time
from datetime import datetime

from .report import CheckReport
from .settings import (IDLE_SECONDS, TEMP_CHECK_INTERVAL, TEMP_MAX_SPREAD_C,
                       TEMP_TOLERANCE_C, TEMP_WAIT_TIMEOUT)


class TemperatureCheck:
    """Reads the CPU temperature every `interval` seconds for `seconds` (one window).
    A window passes when it is
      - stable: max - min <= max_spread_c, and
      - near idle: mean <= reference_c + tolerance_c (skipped if no reference).
    Otherwise it reads another window, until one passes or `timeout` seconds pass.

        report = TemperatureCheck(CpuTemperature()).run(reference_c=38.0)
        report.passed                 # True / False, None = no sensor
        report.data["idle_temperature_c"]   # mean of the last window
    """

    def __init__(self, temperature):
        self.temperature = temperature

    def run(self, reference_c=None, seconds=IDLE_SECONDS, interval=TEMP_CHECK_INTERVAL,
            tolerance_c=TEMP_TOLERANCE_C, max_spread_c=TEMP_MAX_SPREAD_C,
            timeout=TEMP_WAIT_TIMEOUT):
        started_at = datetime.now().isoformat(timespec="seconds")
        if not self.temperature.available:
            return CheckReport("temperature", passed=None, data={"sensor": None},
                               lines=["no x86_pkg_temp sensor - temperature not checked"],
                               started_at=started_at)

        t_start = time.monotonic()
        windows = []
        while True:
            window = self._read_window(seconds, interval)
            window["stable"] = window["max_c"] - window["min_c"] <= max_spread_c
            window["near_idle"] = reference_c is None or window["mean_c"] <= reference_c + tolerance_c
            window["ok"] = window["stable"] and window["near_idle"]
            windows.append(window)
            print(f"[temperature] window {len(windows)}: mean {window['mean_c']:.1f} degC, "
                  f"spread {window['max_c'] - window['min_c']:.1f} -> "
                  f"{'ok' if window['ok'] else 'waiting'}", flush=True)
            if window["ok"] or time.monotonic() - t_start > timeout:
                break

        last = windows[-1]
        waited = time.monotonic() - t_start
        rule = f"spread <= {max_spread_c} degC"
        if reference_c is not None:
            rule += f", mean <= {reference_c:.1f} + {tolerance_c} degC"
        lines = [
            f"CPU temperature every {interval} s for {seconds} s ({rule})",
            f"{len(windows)} window(s), {waited:.0f} s; last window: mean {last['mean_c']:.1f}, "
            f"min {last['min_c']:.1f}, max {last['max_c']:.1f} degC",
            "stable and near idle" if last["ok"] else
            f"WARNING: not stable / near idle after {waited:.0f} s",
        ]
        data = {
            "sensor": self.temperature.zone,
            "reference_c": reference_c,
            "tolerance_c": tolerance_c,
            "max_spread_c": max_spread_c,
            "idle_temperature_c": last["mean_c"],
            "waited_seconds": waited,
            "n_windows": len(windows),
            "windows": windows,
        }
        return CheckReport("temperature", passed=last["ok"], data=data, lines=lines,
                           started_at=started_at)

    def _read_window(self, seconds, interval):
        n = max(1, round(seconds / interval))
        t0 = time.monotonic()
        readings = []
        for i in range(n):
            readings.append({"t_s": round(time.monotonic() - t0, 3),
                             "temp_c": self.temperature.read()})
            if i < n - 1:
                time.sleep(interval)
        temps = [r["temp_c"] for r in readings]
        return {"min_c": min(temps), "mean_c": statistics.fmean(temps), "max_c": max(temps),
                "readings": readings}
