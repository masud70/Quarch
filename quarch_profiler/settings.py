"""All settings in one place.

The first part holds what you may want to change. The second part holds facts
about the meter and internal names; leave those as they are.
"""

# ======================================================================
# You may change these
# ======================================================================

# --- Meter -------------------------------------------------------------
DEVICE = "USB::QTL2843-03-023"      # the meter (see QuarchMeter.list_devices())
PORTS = ("L1",)                     # meter ports the machine is plugged into
CONNECT_TIMEOUT = 5                 # s, how long QIS may take to find the meter

# --- Runs --------------------------------------------------------------
RUNS_DIR = "runs"                   # each run goes to RUNS_DIR/<date>_<time>_<file>/
IDLE_SECONDS = 30                   # s, idle power recording and each temperature window
ZOOM_CYCLES = 3                     # AC cycles shown in the zoomed plots

# --- Temperature check (before the run and before every repetition) ----
# Before the run: a window of IDLE_SECONDS with max - min <= TEMP_SPREAD_C sets
# the reference (its mean). Before every repetition: every reading in the window
# must be within reference +- TEMP_SPREAD_C. Otherwise another window is read.
TEMP_CHECK_INTERVAL = 1             # s between readings
TEMP_SPREAD_C = 1.0                 # degC
TEMP_WAIT_TIMEOUT = 1200            # s, give up and stop the run after this

# --- CPU usage check (once, report only) -------------------------------
CPU_CHECK_SECONDS = 30              # s, length of the check
CPU_CHECK_INTERVAL = 1              # s between readings
CPU_IDLE_PERCENT = 5                # %, mean usage at or below this counts as idle
CPU_TOP_PROCESSES = 10              # busiest processes listed in the report

# --- Process check (once) ----------------------------------------------
PROCESS_TOP_N = 15                  # your busiest processes offered for closing
PROCESS_CLOSE_TIMEOUT = 5           # s to wait for a process to exit
PROTECTED_PROCESS_NAMES = (         # never offered: exact process names
    "systemd", "login", "sshd", "dbus-daemon", "dbus-broker", "tmux", "tmux: server",
    "screen", "gdm", "gdm-x-session", "gnome-shell", "gnome-session-binary", "Xorg", 
    "Xwayland", "pipewire", "pulseaudio",
)
PROTECTED_CMDLINE_PARTS = ("qis", "quarch")     # never offered: in the command line (QIS)


# ======================================================================
# Fixed: leave these as they are
# ======================================================================

# --- Meter facts -------------------------------------------------------
SAMPLE_RATE_HZ = 8000                           # samples per second, set by the meter
SAMPLE_SECONDS = 1 / SAMPLE_RATE_HZ             # 125 us per sample
ALL_PORTS = ("L1", "L2", "L3")
STREAM_COLUMNS = (                              # columns of every streamed row
    "time_us",
    "L1_mA", "L1_mV",
    "L2_mA", "L2_mV",
    "L3_mA", "L3_mV",
    "Neutral_mA",
)
DRAIN_STALL_SECONDS = 10            # s without new samples before the meter counts as stuck

# --- How the runner tells your file where to record --------------------
ENV_RUN_DIR = "QUARCH_RUN_DIR"
ENV_REPETITION = "QUARCH_REPETITION"
ENV_BASELINE_WATTS = "QUARCH_BASELINE_WATTS"
ENV_DEVICE = "QUARCH_DEVICE"
