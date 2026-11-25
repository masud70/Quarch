"""Temperature check: wait until the CPU temperature is at its idle reference."""

import statistics
import time
from datetime import datetime

from .report import CheckReport
from .settings import IDLE_SECONDS, TEMP_CHECK_INTERVAL, TEMP_SPREAD_C, TEMP_WAIT_TIMEOUT


class TemperatureCheck:
    """Reads the CPU temperature every `interval` seconds for `seconds` (one window)
    and repeats until a window passes, or `timeout` seconds pass:

      - no reference yet (before the run): max - min <= spread_c.
        The window's mean then becomes the reference.
      - with a reference: every reading is within reference_c +- spread_c.

        report = TemperatureCheck(CpuTemperature()).run(reference_c=38.0)
        report.passed                       # True / False, None = no sensor
        report.data["idle_temperature_c"]   # mean of the last window
    """

    def __init__(self, temperature):
        self.temperature = temperature

    def run(self, reference_c=None, seconds=IDLE_SECONDS, interval=TEMP_CHECK_INTERVAL,
            spread_c=TEMP_SPREAD_C, timeout=TEMP_WAIT_TIMEOUT):
        started_at = datetime.now().isoformat(timespec="seconds")
        if not self.temperature.available:
            return CheckReport("temperature", passed=None, data={"sensor": None},
                               lines=["no x86_pkg_temp sensor - temperature not checked"],
                               started_at=started_at)

        t_start = time.monotonic()
        windows = []
        while True:
            window = self._read_window(seconds, interval)
            window["ok"] = self._passes(window, reference_c, spread_c)
            windows.append(window)
            print(f"[temperature] window {len(windows)}: {window['min_c']:.1f} to "
                  f"{window['max_c']:.1f} degC -> {'ok' if window['ok'] else 'waiting'}",
                  flush=True)
            if window["ok"] or time.monotonic() - t_start > timeout:
                break

        last = windows[-1]
        waited = time.monotonic() - t_start
        if reference_c is None:
            rule = f"max - min <= {spread_c} degC (sets the reference)"
        else:
            rule = f"every reading in {reference_c:.1f} +- {spread_c} degC"
        lines = [
            f"CPU temperature every {interval} s for {seconds} s: {rule}",
            f"{len(windows)} window(s), {waited:.0f} s; last window {last['min_c']:.1f} to "
            f"{last['max_c']:.1f} degC, mean {last['mean_c']:.1f}",
            "at idle temperature" if last["ok"] else
            f"WARNING: not at idle temperature after {waited:.0f} s",
        ]
        data = {
            "sensor": self.temperature.zone,
            "reference_c": reference_c,
            "spread_c": spread_c,
            "idle_temperature_c": last["mean_c"],
            "waited_seconds": waited,
            "n_windows": len(windows),
            "windows": windows,
        }
        return CheckReport("temperature", passed=last["ok"], data=data, lines=lines,
                           started_at=started_at)

    @staticmethod
    def _passes(window, reference_c, spread_c):
        if reference_c is None:
            return window["max_c"] - window["min_c"] <= spread_c
        return (window["min_c"] >= reference_c - spread_c
                and window["max_c"] <= reference_c + spread_c)

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
