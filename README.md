# quarch_profiler

Measure how much **wall energy** a Python function or a block of code uses, with a
Quarch power meter. You get the total energy, the energy above idle, power
statistics and the CPU temperature. You can also keep every sample the meter
recorded (8,000 per second).

```python
from quarch_profiler import QuarchProfiler

profiler = QuarchProfiler()

@profiler.measure("fit")
def train(X, y):
    return clf.fit(X, y)

train(X, y)
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
- [Options](#options)
- [What a measurement contains](#what-a-measurement-contains)
- [Saving results](#saving-results)
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
| A Quarch power meter on USB | Default `USB::QTL2843-03-023`; see [Choosing the meter](#choosing-the-meter). |
| Linux | Only needed for the CPU temperature. On other systems the temperature is `NaN` and everything else still works. |

```bash
pip install quarchpy numpy pandas
```

The package is the `quarch_profiler/` folder. Run your script from this folder, or
add the folder to `PYTHONPATH`, so that `import quarch_profiler` works.

## Before you measure

1. **Close Quarch Power Studio (QPS).** It runs its own QIS, which blocks this one.
2. Make sure the meter is plugged in and powering the machine you are measuring.
3. Keep the machine as quiet as possible: close the IDE, browsers and anything else
   that uses the CPU. Background work shows up in the wall-power reading.

You do not need to start QIS yourself. The profiler starts it on the first
measurement if it is not already running.

## Quick start

```python
from quarch_profiler import QuarchProfiler

profiler = QuarchProfiler(save_dir="profiles")   # save every measurement here
profiler.measure_idle(30)                        # 30 s of idle power, subtracted from now on

@profiler.measure("fit")
def train(X, y):
    return clf.fit(X, y)

train(X, y)                                      # runs normally and returns the usual value

with profiler.segment("predict") as seg:
    y_pred = clf.predict(X_test)

print(train.last.energy_above_idle_joules)
print(seg.result.energy_above_idle_joules)
```

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
train.measurements.clear()      # forget them
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

Even when it does nothing, the machine draws power (about 47–50 W on our desktop).
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
profiler = QuarchProfiler(baseline_watts=47.2)
```

Measure idle power when the machine is truly idle: no IDE, no other programs, and
the CPU cooled down.

---

## Options

Defaults are set once on the profiler and apply to every measurement:

```python
profiler = QuarchProfiler(
    device="USB::QTL2843-03-023",   # which meter
    baseline_watts=None,            # idle power to subtract (None = do not subtract)
    save_dir=None,                  # folder to save every measurement to (None = do not save)
    keep_samples=True,              # keep every sample in memory
)
```

Any measurement can override them:

```python
@profiler.measure("fit", keep_samples=False, save_dir="fit_runs")
def train(X, y): ...

with profiler.segment("warm-up", baseline_watts=None, save_dir=None):
    ...
```

| Option | Where | Meaning |
|---|---|---|
| `baseline_watts` | profiler, `measure`, `segment` | Idle power to subtract |
| `save_dir` | profiler, `measure`, `segment` | Save each measurement to this folder |
| `keep_samples` | profiler, `measure`, `segment` | Keep the per-sample table in memory |
| `record_args` | `measure` | Store the call's arguments |
| `extra` | `segment` | Any dict stored with the result |

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
| `extra` | Function name, call number, arguments, or your own dict |
| `samples` | Table with one row per sample (or `None` if `keep_samples=False`) |

`m.summary()` gives all of this except the samples as a plain `dict`.

### The samples table

`m.samples` is a pandas DataFrame with one row every 125 microseconds:

| Column | Meaning |
|---|---|
| `time_us`, `t_s` | Time since the recording started (microseconds, seconds) |
| `L1_mA`, `L1_mV` | Current and voltage on line 1 at that instant |
| `L2_mA`, `L2_mV`, `L3_mA`, `L3_mV` | The same for lines 2 and 3 |
| `Neutral_mA` | Current on the neutral (return) wire |
| `watts` | Power at that instant |

**About L1, L2 and L3.** The meter supports three-phase power, so it always reports
three lines. A normal desktop uses only **L1**. L2 and L3 carry no load and show
only a few milliamps of sensor noise, which adds up to about −1 W. `watts` adds all
three lines together, so `joules` and `mean_watts` are about 1 W lower than the true
L1 power. When you subtract idle power, this offset mostly cancels.

Example: plot the power of one measurement.

```python
import matplotlib.pyplot as plt

s = train.last.samples
plt.plot(s["t_s"], s["watts"].rolling(800).mean())   # 0.1 s moving average
plt.xlabel("time (s)"); plt.ylabel("power (W)")
plt.show()
```

---

## Saving results

With `save_dir` set, each measurement writes two files:

```
profiles/
├── 20261124_142049_497548_fit_summary.json   # every field except the samples
└── 20261124_142049_497548_fit_samples.csv    # the samples table (if keep_samples=True)
```

You can also save by hand:

```python
train.last.save("profiles")
train.measurements.to_frame().to_csv("fit_runs.csv", index=False)
```

**Memory:** samples take about 0.6 MB per second of recording. For many or long
runs, use `keep_samples=False` with `save_dir` (if you still want the samples on
disk), or call `train.measurements.clear()` from time to time.

---

## Choosing the meter

```python
from quarch_profiler import QuarchMeter, QuarchProfiler

QuarchMeter.list_devices()
# {'USB::QTL2843-03-023': 'QTL2843-03-023'}

profiler = QuarchProfiler("USB::QTL2843-03-023")
```

To change the default for everyone, edit `DEVICE` in
`quarch_profiler/settings.py`.

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
  only your code. Keep the machine quiet and subtract idle power.

---

## Troubleshooting

| Message | What to do |
|---|---|
| `meter replied 'FAIL: ...'` or `'Connection Timeout'` | The meter is stuck. Close QIS (`python3 -c "from quarchpy.qis import closeQis; closeQis()"`), unplug and replug the meter's USB, and try again. |
| `no data from the meter for 10 s` | Same as above. |
| `QIS buffer overrun - data was lost` | QIS could not keep up. Close other programs; measure shorter pieces of code. |
| `a Quarch recording is already running - recordings cannot nest` | A measured function was called inside another measurement. See [Rules and limits](#rules-and-limits). |
| `already connected to ... - call close() first` | You changed the meter while connected. Call `profiler.close()` first. |
| Cannot connect at all | Make sure Quarch Power Studio is closed, and check the meter's name with `QuarchMeter.list_devices()`. |
| `cpu_temp_*` is `NaN` | The machine has no `x86_pkg_temp` sensor (e.g. not Linux, or not Intel). Energy results are unaffected. |

To check the CPU temperature sensor on its own:

```bash
python3 quarch_profiler/temperature.py
```

---

## How the code is organised

```
quarch_profiler/
├── __init__.py      what you can import
├── profiler.py      QuarchProfiler    — the object you use
├── decorator.py     MeasuredFunction  — a function wrapped by @profiler.measure
├── segment.py       Segment           — a block measured by `with profiler.segment()`
├── measurement.py   Measurement, MeasurementLog — results, saving, to_frame()
├── meter.py         QuarchMeter       — talks to the meter through quarchpy
├── samples.py       SampleParser      — raw meter text → samples table
├── temperature.py   CpuTemperature    — CPU temperature
└── settings.py      device name, sample rate, column names
```

How one measurement works:

1. `QuarchMeter` connects through QIS (starting it if needed) and sends `rec stream`.
2. Your code runs, timed with `time.perf_counter()`. The CPU temperature is read just
   before the recording starts and again at the end, while it is still running.
3. `rec stop` ends the recording, and every sample is read back from QIS.
4. `SampleParser` turns the text into a table and computes `watts = Σ (mA × mV) / 10⁶`
   for each sample.
5. `Measurement` adds up the energy (`joules = Σ watts × 125 µs`), subtracts idle power
   and, if asked, saves the files.
