"""CPU usage check: how busy is the machine?"""

import os
import statistics
import time
from datetime import datetime

import psutil

from .report import CheckReport
from .settings import (CPU_CHECK_INTERVAL, CPU_CHECK_SECONDS, CPU_IDLE_PERCENT,
                       CPU_TOP_PROCESSES)


class CpuUsageCheck:
    """Reads CPU usage every `interval` seconds for `seconds`, then reports the
    whole-machine usage, the usage of every core and the busiest processes.

        report = CpuUsageCheck().run(seconds=10, interval=1)
        report.data["mean_percent"]
    """

    def __init__(self, idle_percent=CPU_IDLE_PERCENT, top_processes=CPU_TOP_PROCESSES):
        self.idle_percent = idle_percent
        self.top_processes = top_processes

    def run(self, seconds=CPU_CHECK_SECONDS, interval=CPU_CHECK_INTERVAL):
        started_at = datetime.now().isoformat(timespec="seconds")
        processes = self._start_process_counters()
        psutil.cpu_percent(percpu=True)             # start the machine counters

        per_core_readings = []
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            per_core_readings.append(psutil.cpu_percent(interval=interval, percpu=True))

        totals = [statistics.fmean(cores) for cores in per_core_readings]
        n_cores = len(per_core_readings[0])
        per_core_mean = [statistics.fmean(r[i] for r in per_core_readings)
                         for i in range(n_cores)]
        top = self._busiest_processes(processes)
        mean_percent = statistics.fmean(totals)
        idle = mean_percent <= self.idle_percent

        data = {
            "seconds": seconds,
            "interval": interval,
            "n_readings": len(totals),
            "n_cores": n_cores,
            "mean_percent": mean_percent,
            "max_percent": max(totals),
            "min_percent": min(totals),
            "per_core_mean_percent": per_core_mean,
            "load_average_1_5_15min": list(os.getloadavg()),
            "idle_limit_percent": self.idle_percent,
            "idle": idle,
            "readings_percent": totals,
            "top_processes": top,
        }
        lines = [
            f"CPU usage over {seconds} s ({len(totals)} readings, {n_cores} cores): "
            f"mean {mean_percent:.1f}%, max {max(totals):.1f}%, min {min(totals):.1f}%",
            f"load average (1/5/15 min): " + ", ".join(f"{x:.2f}" for x in os.getloadavg()),
            "per core mean %: " + " ".join(f"{p:.0f}" for p in per_core_mean),
            ("machine is idle" if idle else "WARNING: machine is busy")
            + f" (idle means mean <= {self.idle_percent}%)",
            f"busiest processes (100% = one full core):",
            *[f"  {p['cpu_percent']:6.1f}%  pid {p['pid']:<7} {p['user'] or '?':<10} {p['name']}"
              for p in top],
        ]
        return CheckReport("cpu", passed=None, data=data, lines=lines, started_at=started_at)

    @staticmethod
    def _start_process_counters():
        """Start each process's CPU counter, so reading it after the window gives
        its average usage over the window."""
        processes = []
        for p in psutil.process_iter(["pid", "name", "username"]):
            try:
                p.cpu_percent(None)
                processes.append(p)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return processes

    def _busiest_processes(self, processes):
        rows = []
        for p in processes:
            try:
                rows.append({"pid": p.pid, "name": p.info["name"], "user": p.info["username"],
                             "cpu_percent": p.cpu_percent(None)})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        rows.sort(key=lambda r: r["cpu_percent"], reverse=True)
        return rows[:self.top_processes]
