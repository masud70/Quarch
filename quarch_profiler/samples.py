"""Turning the meter's raw text into a table of samples."""

import pandas as pd

from .settings import STREAM_COLUMNS


class SampleParser:
    """Parses the raw stream text of one recording.

        parser = SampleParser()
        df = parser.parse(raw)       # one row per 125 us sample

    The DataFrame has every column the meter sends, plus:
        t_s    seconds since the recording started (meter clock)
        watts  power of that sample
    """

    def __init__(self, columns=STREAM_COLUMNS):
        self.columns = tuple(columns)

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
        df["watts"] = self.watts(df)
        return df

    @staticmethod
    def watts(df):
        """Power of every sample. These are instantaneous AC values, so power is
        current x voltage at each sample (not RMS current x RMS voltage).
        mA x mV / 1e6 = W."""
        return (df["L1_mA"] * df["L1_mV"]
                + df["L2_mA"] * df["L2_mV"]
                + df["L3_mA"] * df["L3_mV"]) / 1e6
