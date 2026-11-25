"""All settings in one place. Edit DEVICE if you use a different meter."""

# ======================================================================
# Meter
# ======================================================================

# Connection string of the meter (see QuarchMeter.list_devices()).
DEVICE = "USB::QTL2843-03-023"

# Seconds to wait for QIS to find the meter when connecting.
CONNECT_TIMEOUT = 5

# The meter streams a fixed 8000 samples per second: one every 125 microseconds.
SAMPLE_RATE_HZ = 8000
SAMPLE_SECONDS = 1 / SAMPLE_RATE_HZ

# Give up reading a recording if no new samples arrive for this long
# (a stuck meter replies "Connection Timeout" forever instead of data).
DRAIN_STALL_SECONDS = 10

# The meter has three output ports. Columns of every streamed row: a timestamp,
# then current (mA) and voltage (mV) of ports L1-L3, then the neutral current.
ALL_PORTS = ("L1", "L2", "L3")
STREAM_COLUMNS = ("time_us", "L1_mA", "L1_mV", "L2_mA", "L2_mV",
                  "L3_mA", "L3_mV", "Neutral_mA")

# Ports whose power counts as the machine's power. The experiment machine is
# plugged into L1; the unused ports only add sensor noise (about -1 W together).
PORTS = ("L1",)


# ======================================================================
# Runs
# ======================================================================

# Every run writes everything to RUNS_DIR/<date>_<time>_<file name>/.
RUNS_DIR = "runs"

# Seconds of idle used for the idle temperature and idle power.
IDLE_SECONDS = 30

# AC cycles shown in the zoomed measurement plots.
ZOOM_CYCLES = 3

# How the runner tells your file (a separate process) where to record.
ENV_RUN_DIR = "QUARCH_RUN_DIR"
ENV_REPETITION = "QUARCH_REPETITION"
ENV_BASELINE_WATTS = "QUARCH_BASELINE_WATTS"
ENV_DEVICE = "QUARCH_DEVICE"


# ======================================================================
# Checks
# ======================================================================

# CPU usage: read every CPU_CHECK_INTERVAL seconds for CPU_CHECK_SECONDS.
CPU_CHECK_SECONDS = 10
CPU_CHECK_INTERVAL = 1
CPU_IDLE_PERCENT = 5        # mean CPU usage at or below this counts as idle
CPU_TOP_PROCESSES = 10      # busiest processes listed in the report

# Temperature: read every TEMP_CHECK_INTERVAL seconds for a window of
# IDLE_SECONDS. A window passes when it is stable (max - min <= TEMP_MAX_SPREAD_C)
# and not more than TEMP_TOLERANCE_C above the idle reference. Otherwise another
# window is read, until one passes or TEMP_WAIT_TIMEOUT seconds have passed.
TEMP_CHECK_INTERVAL = 1
TEMP_MAX_SPREAD_C = 1.0
TEMP_TOLERANCE_C = 2.0
TEMP_WAIT_TIMEOUT = 1200

# Processes: how many of your busiest processes to offer for closing.
PROCESS_TOP_N = 15
# Seconds to wait for a process to exit after asking it to close.
PROCESS_CLOSE_TIMEOUT = 5
# Never offered for closing: matched against the process name (exact) ...
PROTECTED_PROCESS_NAMES = (
    "systemd", "sshd", "dbus-daemon", "dbus-broker", "tmux", "tmux: server", "screen",
    "gnome-shell", "gnome-session-binary", "Xorg", "Xwayland", "pipewire", "pulseaudio",
    "gdm", "gdm-x-session", "login",
)
# ... or contained in the command line (lower case). QIS must keep running.
PROTECTED_CMDLINE_PARTS = ("qis", "quarch")
