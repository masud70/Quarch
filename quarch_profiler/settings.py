"""Fixed settings of the Quarch meter. Edit DEVICE if you use a different meter."""

# Connection string of the meter. Find yours with quarch_profiler.list_devices(),
# or switch at run time with quarch_profiler.set_device(...).
DEVICE = "USB::QTL2843-03-023"

# The meter streams a fixed 8000 samples per second: one every 125 microseconds.
SAMPLE_RATE_HZ = 8000
SAMPLE_SECONDS = 1 / SAMPLE_RATE_HZ

# Give up reading a recording if no new samples arrive for this long
# (a stuck meter replies "Connection Timeout" forever instead of data).
DRAIN_STALL_SECONDS = 10

# Columns of every streamed row: a timestamp, then current (mA) and voltage (mV)
# of the three lines L1-L3, then the neutral current.
STREAM_COLUMNS = ("time_us", "L1_mA", "L1_mV", "L2_mA", "L2_mV",
                  "L3_mA", "L3_mV", "Neutral_mA")
