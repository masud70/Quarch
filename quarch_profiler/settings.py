"""Fixed settings of the Quarch meter. Edit DEVICE if you use a different meter."""

# Connection string of the meter. Find yours with quarch_profiler.list_devices(),
# or switch at run time with quarch_profiler.set_device(...).
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
# Run folder
# ======================================================================

# Every QuarchProfiler writes all its reports to RUNS_DIR/<date_time>_<name>/.
RUNS_DIR = "runs"


# ======================================================================
# Checks before measuring (also callable any time)
# ======================================================================

# CPU usage: read every CPU_CHECK_INTERVAL seconds for CPU_CHECK_SECONDS.
CPU_CHECK_SECONDS = 10
CPU_CHECK_INTERVAL = 1
CPU_IDLE_PERCENT = 5        # mean CPU usage at or below this counts as idle
CPU_TOP_PROCESSES = 10      # busiest processes listed in the report

# Temperature: read every TEMP_CHECK_INTERVAL seconds for TEMP_CHECK_SECONDS;
# if any reading is above TEMP_LIMIT_C, read another window, until it is cool
# or TEMP_WAIT_TIMEOUT seconds have passed.
TEMP_CHECK_SECONDS = 30
TEMP_CHECK_INTERVAL = 1
TEMP_LIMIT_C = 55.0
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
