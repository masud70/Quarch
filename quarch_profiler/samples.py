"""Turning the meter's raw text into a table of samples."""

import pandas as pd

from .settings import ALL_PORTS, PORTS, STREAM_COLUMNS


class SampleParser:
    """Parses the raw stream text of one recording.

        parser = SampleParser()              # counts the ports in settings.PORTS
        df = parser.parse(raw)               # one row per 125 us sample

    The DataFrame has every column the meter sends, plus:
        t_s                 seconds since the recording started (meter clock)
        L1_W, L2_W, L3_W    power of each port
        watts               power of the ports in `ports` (the machine's power)
    """

    def __init__(self, columns=STREAM_COLUMNS, ports=PORTS):
        unknown = set(ports) - set(ALL_PORTS)
        if not ports or unknown:
            raise ValueError(f"ports must be a non-empty subset of {ALL_PORTS}, got {ports}")
        self.columns = tuple(columns)
        self.ports = tuple(ports)

    def parse(self, raw):
        rows = []
        for line in raw.splitlines():
            parts = line.split()
            if len(parts) != len(self.columns):
                continue
            try:
                rows.append([float(p) for p in parts])
            except ValueError:
                continue                # header or status line
        df = pd.DataFrame(rows, columns=list(self.columns))
        df.insert(1, "t_s", df["time_us"] / 1e6)
        # Instantaneous AC values, so power is current x voltage at each sample
        # (not RMS current x RMS voltage). mA x mV / 1e6 = W.
        for port in ALL_PORTS:
            df[f"{port}_W"] = df[f"{port}_mA"] * df[f"{port}_mV"] / 1e6
        df["watts"] = df[[f"{port}_W" for port in self.ports]].sum(axis=1)
        return df
