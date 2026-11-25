"""Command line: python3 -m quarch_profiler <file> [-n N] [--idle-seconds S] [-- file args]"""

import argparse
import sys

from .runner import Runner
from .settings import DEVICE, IDLE_SECONDS


def main():
    # Everything after "--" goes to your file, not to the runner.
    argv = sys.argv[1:]
    script_args = []
    if "--" in argv:
        split = argv.index("--")
        argv, script_args = argv[:split], argv[split + 1:]

    ap = argparse.ArgumentParser(
        prog="python3 -m quarch_profiler",
        description="Run a file that uses @measure / segment, record its wall energy "
                    "with the Quarch meter, and save reports and plots to runs/.")
    ap.add_argument("script", help="your Python file")
    ap.add_argument("-n", "--repeat", type=int, default=1,
                    help="how many times to run the file (default 1)")
    ap.add_argument("--idle-seconds", type=float, default=IDLE_SECONDS,
                    help=f"length of the idle temperature / power check (default {IDLE_SECONDS})")
    ap.add_argument("--device", default=DEVICE, help=f"meter (default {DEVICE})")
    args = ap.parse_args(argv)

    Runner(args.script, repeat=args.repeat, idle_seconds=args.idle_seconds,
           script_args=script_args, device=args.device).start()


if __name__ == "__main__":
    main()
