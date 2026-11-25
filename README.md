# quarch_profiler

Measure how much **wall energy** a Python function or a block of code uses, with a
Quarch power meter. You get the total energy, the energy above idle, power
statistics and the CPU temperature. You can also keep every sample the meter
recorded (8,000 per second).

Before measuring, it checks the machine: it lists the background processes (and
closes the ones you choose), reports the CPU usage, and waits until the CPU is
cool. Every report and measurement of a run goes into one folder.

```python
from quarch_profiler import QuarchProfiler

profiler = QuarchProfiler(name="rf_mnist")

@profiler.measure("fit")
def train(X, y):
    return clf.fit(X, y)

train(X, y)                       # checks run first, then the call is measured
print(train.last.joules)          # energy of that call, in joules
```

---

## Contents

- [Requirements](#requirements)
- [Before you measure](#before-you-measure)
- [Quick start](#quick-start)
- [Measuring a function](#1-measuring-a-function)
- [Measuring a block of code](#2-measuring-a-block-of-code)
- [Subtracting idle power](#subtracting-idle-power)
- [Machine checks](#machine-checks)
- [The run folder](#the-run-folder)
- [Options](#options)
- [What a measurement contains](#what-a-measurement-contains)
- [Choosing the meter](#choosing-the-meter)
- [Rules and limits](#rules-and-limits)
- [Troubleshooting](#troubleshooting)
- [How the code is organised](#how-the-code-is-organised)

---

## Requirements

| What | Notes |
|---|---|
| Python **3.10+** | |
| `quarchpy` | Talks to the meter. Tested against version 2.2.24. QIS (Quarch Instrument Server) comes bundled with it. |
| `numpy`, `pandas` | |
| `psutil` | CPU usage and the process list |
| A Quarch power meter on USB | Default `USB::QTL2843-03-023`; see [Choosing the meter](#choosing-the-meter). |
| Linux | Only needed for the CPU temperature. On other systems the temperature is `NaN` and the temperature check is skipped. |

```bash
pip install quarchpy numpy pandas psutil
```

The package is the `quarch_profiler/` folder. Run your script from this folder, or
add the folder to `PYTHONPATH`, so that `import quarch_profiler` works.

## Before you measure

1. **Close Quarch Power Studio (QPS).** It runs its own QIS, which blocks this one.
2. Make sure the experiment machine is plugged into port **L1** of the meter.
3. **Run your script from a terminal.** The process check asks you which processes to
   close, so it needs a terminal to type in. Without one (e.g. `nohup`), it only reports.

You do not need to start QIS yourself. The profiler starts it on the first
measurement if it is not already running.

## Quick start

```python
from quarch_profiler import QuarchProfiler

profiler = QuarchProfiler(name="rf_mnist")    # creates runs/<date_time>_rf_mnist/
profiler.measure_idle(30)                     # runs the checks, then 30 s of idle power

@profiler.measure("fit")
def train(X, y):
    return clf.fit(X, y)

train(X, y)                                   # runs normally and returns the usual value

with profiler.segment("predict") as seg:
    y_pred = clf.predict(X_test)

print(train.last.energy_above_idle_joules)
print(seg.result.energy_above_idle_joules)
```

What happens:

1. `QuarchProfiler(...)` creates the run folder.
2. Before the **first** measurement (here `measure_idle`), the
   [machine checks](#machine-checks) run: processes, CPU usage, temperature.
3. Each measurement is saved to the run folder and printed.

---

## 1. Measuring a function

Put `@profiler.measure(...)` above the function. **Every call** is measured, and
the function returns exactly what it normally returns.

```python
@profiler.measure("fit")
def train(X, y):
    return clf.fit(X, y)

for _ in range(10):
    train(X, y)

train.last                      # Measurement of the newest call
train.measurements              # all calls (a list)
train.measurements.to_frame()   # all calls as a pandas DataFrame
train.measurements.clear()      # forget them (the saved files stay)
```

Without arguments, the label is the function's name:

```python
@profiler.measure
def preprocess(data): ...
```

It also works on methods inside a class:

```python
class Experiment:
    @profiler.measure("run")
    def run(self, x): ...

Experiment().run(5)
Experiment.run.last
```

To store the call's arguments with each result, use `record_args=True`:

```python
@profiler.measure("fit", record_args=True)
def train(n_trees): ...

train(100)
train.last.extra    # {'function': '__main__.train', 'call_index': 1, 'args': ['100'], 'kwargs': {}}
```

## 2. Measuring a block of code

Wrap any lines in `with profiler.segment(...)`. The result is in `.result` after
the block ends.

```python
with profiler.segment("load + fit") as seg:
    X, y = load_data()
    clf.fit(X, y)

seg.result.joules
seg.result.samples
```

You can attach your own information to the result with `extra`:

```python
with profiler.segment("fit", extra={"dataset": "mnist", "trees": 100}) as seg:
    clf.fit(X, y)
```

---

## Subtracting idle power

Even when it does nothing, the machine draws power (about 50 W on our desktop).
To get the energy that **your code** used, subtract the idle power:

```python
profiler.measure_idle(30)            # 1 recording of 30 s
profiler.measure_idle(30, 5)         # or the average of 5 recordings
profiler.baseline_watts              # the stored value
```

From then on, every measurement fills in `energy_above_idle_joules`:

```
energy_above_idle_joules = joules - baseline_watts × window_seconds
```

If you already know the idle power, set it directly:

```python
profiler = QuarchProfiler(baseline_watts=50.4)
```

---

## Machine checks

Three checks make sure the machine is in a fair state before you measure.

**Before the first measurement**, they run automatically, in this order:

1. **Processes:** close what you don't need.
2. **CPU usage:** is the machine idle now?
3. **Temperature:** wait until the CPU is cool.

If the CPU does not cool down in time, the profiler raises `RuntimeError` and
does not measure. The next measurement runs the checks again.

**You can also run any check at any time**, e.g. between experiments:

```python
profiler.check_processes()
profiler.check_cpu(seconds=10, interval=1)
profiler.check_temperature(seconds=30, interval=1)
```

Each check prints its report and saves it to the run folder. It also returns a
`CheckReport`: `report.passed`, `report.data` (every number) and `report.text`.

To turn the automatic checks off, use `QuarchProfiler(prechecks=False)`. You can
still call them yourself, or all three in order with `profiler.run_prechecks()`.

### Processes

```python
profiler.check_processes()
```

1. Lists **every** running process with its CPU and memory use. The full list goes to
   the report file.
2. Shows **your** busiest processes that can be closed, numbered:
   ```
     #    CPU%       MB  PID      NAME / COMMAND
     1    49.9      743  639704   chrome  /opt/google/chrome/chrome --type=renderer ...
     2    21.8      721  5731     chrome  /opt/google/chrome/chrome
   Close which? Numbers separated by spaces (e.g. 1 3), 'all', or Enter for none: 1 2
   Close chrome (639704), chrome (5731)? [y/N]: y
   ```
3. Closes only what you chose and confirmed with `y`.

**Safety rules:**
- Nothing is closed without your confirmation. Pressing Enter closes nothing.
- Only **your own** processes are offered. Other users' and system processes never are.
- **Never offered:** your script itself, its parents (your shell, terminal, IDE) and
  its children. The same goes for QIS and processes such as `sshd`, `systemd`,
  `tmux` and `gnome-shell`. See `PROTECTED_PROCESS_NAMES` and
  `PROTECTED_CMDLINE_PARTS` in `settings.py`.
- Processes are **asked** to exit (SIGTERM), never force-killed, so programs can
  save their work. Any that are still running after 5 s are listed in the report.
- **Without a terminal** (e.g. `nohup python run.py &`), nothing is closed: the check
  only reports. Use `check_processes(interactive=False)` to force report-only.

### CPU usage

```python
profiler.check_cpu(seconds=10, interval=1)   # one reading every 1 s for 10 s
```

The report shows:
- the whole machine's CPU usage: mean, max and min;
- the mean usage of every core;
- the load average;
- the 10 busiest processes over that time. 100% means one full core.

If the mean is above 5% (`CPU_IDLE_PERCENT`), it prints a warning that the machine
is busy. This check only reports; it never stops a run.

### Temperature

```python
profiler.check_temperature(seconds=30, interval=1, limit_c=55, wait=True, timeout=1200)
```

1. Reads the CPU temperature every `interval` seconds for `seconds`. This is one
   *window*.
2. If any reading is above `limit_c`, it reads another window, and keeps going until a
   whole window is cool or `timeout` seconds have passed.
3. It reports the start, end, min, mean, max and trend of the last window, and how
   long it waited.

With `wait=False` it reads one window and only reports.

`report.passed` is `True` when cool, `False` when still hot, and `None` when the
machine has no temperature sensor.

---

## The run folder

Each `QuarchProfiler` gets its own folder, and **everything** from that run goes into it:

```
runs/20261125_141428_rf_mnist/
├── run_info.json          when, which machine, device, ports, settings
├── report.txt             every check and measurement, readable, in order
├── measurements.csv       one row per measurement (all fields except samples)
├── checks/
│   ├── 141429_processes.json
│   ├── 141431_cpu.json
│   └── 141432_temperature.json
└── measurements/
    ├── 20261125_141432_502998_idle_summary.json
    ├── 20261125_141432_533362_fit_summary.json
    └── 20261125_141432_533362_fit_samples.csv
```

- Use `QuarchProfiler(name=...)` to name the folder, and `runs_dir=...` to put it
  somewhere other than `runs/`.
- `profiler.run.path` is the folder.
- `report.txt` is the place to start reading. `measurements.csv` loads straight into
  pandas: `pd.read_csv(profiler.run.measurements_csv)`.

**Samples on disk and in memory.** Samples take about 1 MB per second of recording.
- `save_samples=False` writes only the summary to disk.
- `keep_samples=False` frees the samples from memory after saving them.

For long experiments, use `keep_samples=False`.

---

## Options

Defaults are set once on the profiler:

```python
profiler = QuarchProfiler(
    device="USB::QTL2843-03-023",   # which meter
    name=None,                      # run folder name: runs/<date_time>_<name>/
    runs_dir="runs",                # where run folders go
    prechecks=True,                 # run the machine checks before the first measurement
    baseline_watts=None,            # idle power to subtract (None = do not subtract)
    keep_samples=True,              # keep every sample in memory
    save_samples=True,              # write every sample to the run folder
    connect_timeout=5,              # seconds QIS may take to find the meter
)
```

Any measurement can override `baseline_watts`, `keep_samples` and `save_samples`:

```python
@profiler.measure("fit", keep_samples=False, save_samples=False)
def train(X, y): ...

with profiler.segment("warm-up", baseline_watts=None):
    ...
```

| Option | Where | Meaning |
|---|---|---|
| `baseline_watts` | profiler, `measure`, `segment` | Idle power to subtract |
| `keep_samples` | profiler, `measure`, `segment` | Keep the per-sample table in memory |
| `save_samples` | profiler, `measure`, `segment` | Write the per-sample table to the run folder |
| `record_args` | `measure` | Store the call's arguments |
| `extra` | `segment` | Any dict stored with the result |
| `name`, `runs_dir`, `prechecks`, `device`, `connect_timeout` | profiler | See above |

The check settings (durations, temperature limit, protected processes, ...) are in
`quarch_profiler/settings.py`.

---

## What a measurement contains

Each measurement (`train.last`, `seg.result`) is a `Measurement` object:

| Field | Meaning |
|---|---|
| `label` | Name you gave it |
| `started_at` | When the recording started (ISO time) |
| `workload_seconds` | How long your code ran |
| `window_seconds` | How long the meter recorded (slightly longer than your code) |
| `n_samples` | Number of samples (8,000 per second) |
| `joules` | **Total wall energy** during the recording |
| `mean_watts`, `peak_watts`, `min_watts`, `std_watts` | Power statistics |
| `baseline_watts`, `baseline_joules` | Idle power and idle energy over the same window |
| `energy_above_idle_joules` | **Energy your code used** (total minus idle) |
| `cpu_temp_start_c`, `cpu_temp_end_c` | CPU temperature before and at the end of the code |
| `device` | Meter used |
| `ports` | Meter ports counted in the power and energy, e.g. `('L1',)` |
| `extra` | Function name, call number, arguments, or your own dict |
| `samples` | Table with one row per sample (or `None` if `keep_samples=False`) |

`m.summary()` gives all of this except the samples as a plain `dict`.

### The samples table

`m.samples` is a pandas DataFrame with one row every 125 microseconds:

| Column | Meaning |
|---|---|
| `time_us`, `t_s` | Time since the recording started (microseconds, seconds) |
| `L1_mA`, `L1_mV` | Current and voltage on output port L1 at that instant |
| `L2_mA`, `L2_mV`, `L3_mA`, `L3_mV` | The same for ports L2 and L3 |
| `Neutral_mA` | Current on the shared neutral (return) wire |
| `L1_W`, `L2_W`, `L3_W` | Power of each port at that instant |
| `watts` | **The machine's power**: the sum of the counted ports (by default only L1) |

**About L1, L2 and L3.** The meter has three output ports, L1, L2 and L3, and
reports current and voltage for each. Our experiment machine is plugged into **L1**.
L2 and L3 are unused: they show the same mains voltage but only a few milliamps of
sensor noise, which would add about −1 W if it were counted. So `watts`, `joules`
and every other power figure count **only L1** by default. The other ports'
readings are still in the samples table.

If you plug the machine into a different port, or measure more than one machine,
change `PORTS` in `quarch_profiler/settings.py`:

```python
PORTS = ("L1",)          # default: the experiment machine on L1
PORTS = ("L2",)          # machine plugged into L2
PORTS = ("L1", "L2")     # total of two machines on L1 and L2
```

Example: plot the power of one measurement.

```python
import matplotlib.pyplot as plt

s = train.last.samples
plt.plot(s["t_s"], s["watts"].rolling(800).mean())   # 0.1 s moving average
plt.xlabel("time (s)"); plt.ylabel("power (W)")
plt.show()
```

---

## Choosing the meter

```python
from quarch_profiler import QuarchMeter, QuarchProfiler

QuarchMeter.list_devices()        # the devices QIS can see (starts QIS if needed)
# ['USB::QTL2843-03-023']

profiler = QuarchProfiler("USB::QTL2843-03-023")
```

To change the default for everyone, edit `DEVICE` in
`quarch_profiler/settings.py`.

When connecting, QIS gets 5 seconds to find the meter. If it needs longer (e.g.
right after QIS starts or the meter is replugged), raise it:

```python
profiler = QuarchProfiler(connect_timeout=15)
```

or change `CONNECT_TIMEOUT` in `settings.py`.

The connection opens on the first measurement and closes automatically when
Python exits. To close it earlier:

```python
profiler.close()

# or
with QuarchProfiler() as profiler:
    ...
```

---

## Rules and limits

- **One recording at a time.** The meter has a single stream, so measurements cannot
  be nested. Calling a measured function inside a `profiler.segment(...)` block raises
  `RuntimeError`. Measure either the outer block or the inner function, not both.
- **Errors in your code.** If the measured code raises an exception, the recording is
  stopped and discarded, and your exception is passed on unchanged. Nothing is saved
  for that run.
- **Very short code is not measured accurately.** Starting and stopping a recording
  adds a small delay at each end of the window, which matters when the code itself
  takes only milliseconds. To measure something short, run it many times inside one
  segment and divide:

  ```python
  N = 1000
  with profiler.segment("predict x1000") as seg:
      for _ in range(N):
          clf.predict(x)
  per_call = seg.result.energy_above_idle_joules / N
  ```
- **Repeat your measurements.** Wall power varies a little from run to run. Measure
  several times and use the mean, or the median, of the results.
- **Two clocks.** `t_s` in the samples is the meter's own clock from the start of the
  recording. It is not synchronised with Python's `time.perf_counter()`, so it lines
  samples up within one recording but not exactly with events in your code.
- **The whole machine is measured.** The meter sees everything the computer does, not
  only your code. Use the checks, and subtract idle power.

---

## Troubleshooting

| Message | What to do |
|---|---|
| `CPU did not cool below 55.0 degC within 1200 s - not measuring` | Something is keeping the CPU busy or the room is warm. Look at the CPU check in `report.txt`, close what is busy, and try again. If 55 °C is too strict for your machine, raise `TEMP_LIMIT_C` in `settings.py`. |
| `WARNING: machine is busy` in the CPU check | Look at the busiest processes in the report, and close them with `check_processes()`. |
| The process check does not ask anything | Your script is not running in a terminal, so the check only reports. |
| A process is listed as `STILL RUNNING` | It ignored the request to exit. Close it yourself. |
| `meter replied 'FAIL: ...'` or `'Connection Timeout'` | The meter is stuck. Close QIS (`python3 -c "from quarchpy.qis import closeQis; closeQis()"`), unplug and replug the meter's USB, and try again. |
| `no data from the meter for 10 s` | Same as above. |
| `QIS buffer overrun - data was lost` | QIS could not keep up. Close other programs; measure shorter pieces of code. |
| `a Quarch recording is already running - recordings cannot nest` | A measured function was called inside another measurement. See [Rules and limits](#rules-and-limits). |
| `already connected to ... - call close() first` | You changed the meter while connected. Call `profiler.close()` first. |
| `Could not find module '...' in QIS within 5s` | QIS did not see the meter in time. Check the name with `QuarchMeter.list_devices()`; if the meter is listed, raise `connect_timeout`. |
| Cannot connect at all | Make sure Quarch Power Studio is closed, and check the meter's name with `QuarchMeter.list_devices()`. An empty list means QIS cannot see the meter: check the USB cable. |
| `cpu_temp_*` is `NaN`, temperature check skipped | The machine has no `x86_pkg_temp` sensor (e.g. not Linux, or not Intel). Energy results are unaffected. |

To check the CPU temperature sensor on its own:

```bash
python3 quarch_profiler/temperature.py
```

---

## How the code is organised

```
quarch_profiler/
├── __init__.py            what you can import
├── profiler.py            QuarchProfiler    — the object you use
├── decorator.py           MeasuredFunction  — a function wrapped by @profiler.measure
├── segment.py             Segment           — a block measured by `with profiler.segment()`
├── measurement.py         Measurement, MeasurementLog — results
├── run_folder.py          RunFolder         — one folder with every report of a run
├── cpu_check.py           CpuUsageCheck     — CPU usage
├── temperature_check.py   TemperatureCheck  — temperature over time, wait until cool
├── process_check.py       ProcessCheck      — running processes, close the ones you choose
├── report.py              CheckReport       — the result of one check
├── meter.py               QuarchMeter       — talks to the meter through quarchpy
├── samples.py             SampleParser      — raw meter text → samples table
├── temperature.py         CpuTemperature    — reads the CPU temperature
└── settings.py            device, ports, run folder and check settings
```

How one measurement works:

1. Before the first measurement, the checks run: processes, CPU usage, temperature.
2. `QuarchMeter` connects through QIS (starting it if needed) and sends `rec stream`.
3. Your code runs, timed with `time.perf_counter()`. The CPU temperature is read just
   before the recording starts and again at the end, while it is still running.
4. `rec stop` ends the recording, and every sample is read back from QIS.
5. `SampleParser` turns the text into a table, computes each port's power
   (`L1_W = L1_mA × L1_mV / 10⁶`, and the same for L2 and L3), and sets `watts` to
   the sum of the counted ports (by default only `L1_W`).
6. `Measurement` adds up the energy (`joules = Σ watts × 125 µs`) and subtracts idle
   power. `RunFolder` saves it and adds it to `measurements.csv` and `report.txt`.
