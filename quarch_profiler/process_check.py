"""Background-process check: list what is running and close what you choose."""

import sys
import time
from datetime import datetime

import psutil

from .report import CheckReport
from .settings import (PROCESS_CLOSE_TIMEOUT, PROCESS_TOP_N, PROTECTED_CMDLINE_PARTS,
                       PROTECTED_PROCESS_NAMES)


class ProcessCheck:
    """Lists every running process, shows your busiest ones and closes the ones
    you pick. Nothing is closed without your confirmation.

    Never offered for closing:
      - processes of other users (and system processes)
      - this script, its parents (shell, terminal, IDE) and its children
      - names in PROTECTED_PROCESS_NAMES and command lines containing
        PROTECTED_CMDLINE_PARTS (e.g. QIS)

    Chosen processes are asked to exit (SIGTERM), not killed; any that are still
    running after PROCESS_CLOSE_TIMEOUT seconds are listed in the report.
    Without a terminal (e.g. under nohup) it only reports.
    """

    def __init__(self, top_n=PROCESS_TOP_N, close_timeout=PROCESS_CLOSE_TIMEOUT,
                 protected_names=PROTECTED_PROCESS_NAMES,
                 protected_cmdline_parts=PROTECTED_CMDLINE_PARTS, ask=input):
        self.top_n = top_n
        self.close_timeout = close_timeout
        self.protected_names = set(protected_names)
        self.protected_cmdline_parts = tuple(protected_cmdline_parts)
        self.ask = ask

    def run(self, interactive=None, sample_seconds=1.0):
        started_at = datetime.now().isoformat(timespec="seconds")
        if interactive is None:
            interactive = sys.stdin.isatty()
        me = psutil.Process()
        user = me.username()
        related = self._related_pids(me)

        processes, rows = self._snapshot(sample_seconds)
        for row in rows:
            row["mine"] = row["user"] == user
            row["protected"] = self._protected_reason(row, related)
        candidates = sorted(
            (r for r in rows if r["mine"] and not r["protected"]),
            key=lambda r: (r["cpu_percent"], r["memory_mb"]), reverse=True)[:self.top_n]

        lines = [f"{len(rows)} processes running, {sum(r['mine'] for r in rows)} of them "
                 f"yours ({user}). Your busiest that can be closed:"]
        lines += self._table(candidates)

        closed, still_running, failed, chosen = [], [], [], []
        if not candidates:
            lines.append("nothing to close")
        elif not interactive:
            lines.append("not running in a terminal - nothing closed (report only)")
        else:
            print("\n".join(lines), flush=True)
            chosen = self._choose(candidates)
            if chosen:
                closed, still_running, failed = self._close(
                    [processes[r["pid"]] for r in chosen])
            lines.append("chosen: " + (", ".join(f"{r['name']} ({r['pid']})" for r in chosen)
                                       or "none"))
            for label, items in (("closed", closed), ("STILL RUNNING", still_running),
                                 ("could not close", failed)):
                if items:
                    lines.append(f"{label}: " + ", ".join(items))

        data = {
            "user": user,
            "interactive": interactive,
            "n_processes": len(rows),
            "n_mine": sum(r["mine"] for r in rows),
            "candidates": candidates,
            "chosen": [r["pid"] for r in chosen],
            "closed": closed,
            "still_running": still_running,
            "failed": failed,
            "all_processes": sorted(rows, key=lambda r: r["cpu_percent"], reverse=True),
        }
        return CheckReport("processes", passed=None, data=data, lines=lines,
                           started_at=started_at)

    # ------------------------------------------------------------- collecting

    @staticmethod
    def _related_pids(me):
        """This process, its parents and its children."""
        pids = {me.pid}
        pids.update(p.pid for p in me.parents())
        pids.update(p.pid for p in me.children(recursive=True))
        return pids

    @staticmethod
    def _snapshot(sample_seconds):
        """Every process with its CPU usage averaged over `sample_seconds`.
        Returns ({pid: psutil.Process}, [row dict, ...])."""
        processes = {}
        for p in psutil.process_iter():
            try:
                p.cpu_percent(None)                 # start its CPU counter
                processes[p.pid] = p
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        time.sleep(sample_seconds)

        rows = []
        for pid, p in list(processes.items()):
            try:
                with p.oneshot():
                    rows.append({
                        "pid": pid,
                        "name": p.name(),
                        "user": p.username(),
                        "cpu_percent": p.cpu_percent(None),
                        "memory_mb": p.memory_info().rss / 2**20,
                        "status": p.status(),
                        "started": time.strftime("%Y-%m-%d %H:%M:%S",
                                                 time.localtime(p.create_time())),
                        "cmdline": " ".join(p.cmdline()),
                    })
            except psutil.NoSuchProcess:
                processes.pop(pid)
            except psutil.AccessDenied:
                rows.append({"pid": pid, "name": "?", "user": None, "cpu_percent": 0.0,
                             "memory_mb": 0.0, "status": "?", "started": None, "cmdline": ""})
        return processes, rows

    def _protected_reason(self, row, related):
        if row["pid"] in related:
            return "this script or its parent/child"
        if row["name"] in self.protected_names:
            return "protected name"
        cmdline = row["cmdline"].lower()
        if any(part in cmdline for part in self.protected_cmdline_parts):
            return "protected command line"
        return None

    @staticmethod
    def _table(rows):
        out = [f"  {'#':>3}  {'CPU%':>6}  {'MB':>7}  {'PID':<7}  NAME / COMMAND"]
        for i, r in enumerate(rows, start=1):
            out.append(f"  {i:>3}  {r['cpu_percent']:6.1f}  {r['memory_mb']:7.0f}  "
                       f"{r['pid']:<7}  {r['name']}  {r['cmdline'][:60]}")
        return out

    # ---------------------------------------------------------------- closing

    def _choose(self, candidates):
        """Ask which to close, then ask to confirm. Returns the chosen rows."""
        while True:
            answer = self.ask("Close which? Numbers separated by spaces (e.g. 1 3), "
                              "'all', or Enter for none: ").strip().lower()
            if not answer:
                return []
            if answer == "all":
                chosen = list(candidates)
            else:
                try:
                    numbers = [int(x) for x in answer.replace(",", " ").split()]
                except ValueError:
                    print("  please type numbers from the list")
                    continue
                if not all(1 <= n <= len(candidates) for n in numbers):
                    print(f"  numbers must be between 1 and {len(candidates)}")
                    continue
                chosen = [candidates[n - 1] for n in dict.fromkeys(numbers)]
            names = ", ".join(f"{r['name']} ({r['pid']})" for r in chosen)
            if self.ask(f"Close {names}? [y/N]: ").strip().lower() == "y":
                return chosen
            return []

    def _close(self, processes):
        """SIGTERM each process and wait. Returns (closed, still_running, failed)
        as lists of "name (pid)"."""
        labels = {p.pid: self._label(p) for p in processes}   # names, while still running
        asked, failed = [], []
        for p in processes:
            try:
                p.terminate()       # psutil checks the pid was not reused
                asked.append(p)
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                failed.append(f"{labels[p.pid]}: {type(e).__name__}")
        gone, alive = psutil.wait_procs(asked, timeout=self.close_timeout)
        return ([labels[p.pid] for p in gone], [labels[p.pid] for p in alive], failed)

    @staticmethod
    def _label(p):
        try:
            return f"{p.name()} ({p.pid})"
        except psutil.Error:
            return f"pid {p.pid}"
