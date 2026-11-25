# quarch_profiler

Measure the **wall energy** of functions and code blocks in your Python file with
a Quarch power meter. Mark what to measure, then let the runner repeat your file
`n` times under controlled conditions. You get every sample, a summary, and plots.

```python
# my_experiment.py
from quarch_profiler import measure, segment

@measure("fit")
def train():
    ...

train()

with segment("predict"):
    ...
```

```bash
python3 -m quarch_profiler my_experiment.py -n 5
```

---

## What the runner does

```
once         1. processes     list them; you choose which to close
             2. CPU usage     report how busy the machine is
             3. temperature   wait until stable -> this is the idle reference
             4. idle power    measure it -> subtracted from every measurement
each rep     5. temperature   wait until within idle reference ± spread
             6. your file     run in a fresh Python process; record every
                              @measure / segment
at the end   7. summary.csv and plots
```

- **Processes (step 1).** Only your own processes are offered, and only those you
  pick and confirm with `y` are closed. Your shell, terminal, IDE, QIS and system
  processes are never offered. Processes are asked to exit (SIGTERM), never
  force-killed. Without a terminal, the check only reports. It runs once per run,
  not before every repetition.
- **Temperature (steps 3 and 5).** The CPU temperature is read every second for
  `--idle-seconds` (default 30), with one setting, the spread (`TEMP_SPREAD_C`, 1 °C):
  - **before the run:** a window passes when max − min ≤ spread. Its mean becomes the
    **idle reference**, fixed for the whole run.
  - **before each repetition:** a window passes when every reading is within
    reference ± spread.

  If a window does not pass, another one is read, until one passes. After 20 minutes
  the run stops.
- **Fresh process per repetition (step 6).** Every repetition starts from the same
  state: no warm imports or caches from the previous one. If your file fails, the
  runner stops and keeps what was recorded so far.

## Command line

```bash
python3 -m quarch_profiler my_experiment.py                  # once
python3 -m quarch_profiler my_experiment.py -n 10            # 10 repetitions
python3 -m quarch_profiler my_experiment.py -n 10 --idle-seconds 60
python3 -m quarch_profiler my_experiment.py -n 5 -- --data mnist --trees 100
```

| Option | Default | Meaning |
|---|---|---|
| `-n`, `--repeat` | 1 | How many times to run your file |
| `--idle-seconds` | 30 | Length of each temperature window and of the idle power measurement |
| `--device` | `USB::QTL2843-03-023` | The meter |
| `-- ...` | | Everything after `--` is passed to your file |

Run it from a terminal, so the process check can ask you questions.

## In your file

| Use | Measures |
|---|---|
| `@measure("label")` | every call of the function (also works on methods) |
| `@measure` | the same, labelled with the function's name |
| `with segment("label"):` | the lines inside the block |

- A label can be measured several times in one repetition; each call is saved
  separately (`call01`, `call02`, ...), and the summary adds them up per repetition.
- **Measurements cannot be nested:** the meter has a single stream, so a measured
  function cannot be called inside another measurement. Doing so raises `RuntimeError`.
- Started on its own (`python3 my_experiment.py`), your file runs normally and
  nothing is measured.

## The run folder

```
runs/20261125_153341_my_experiment/
├── run_info.json          file, arguments, repetitions, idle reference, idle power
├── report.txt             everything that happened, readable, in order  <- start here
├── summary.csv            one row per label: mean, std, min, max over the repetitions
├── measurements.csv       one row per measurement
├── checks/
│   ├── 153341_processes.json
│   ├── 153342_cpu.json
│   ├── 153352_temperature_rep00.json     the idle reference check
│   ├── 153405_temperature_rep01.json     before repetition 1
│   └── ...
├── measurements/
│   ├── idle/rep00_call01_summary.json + rep00_call01_samples.csv
│   ├── fit/rep01_call01_summary.json  + rep01_call01_samples.csv
│   └── predict/...
└── plots/
    ├── energy_per_repetition.png         one panel per label
    ├── energy_boxplot.png                energy of every 1-second piece: idle + each repetition
    ├── temperature.png                   temperature before each repetition vs. reference ± spread
    ├── fit/rep01_call01.png              voltage, current, power, energy (whole recording)
    ├── fit/rep01_call01_zoom.png         the same for the first 3 AC cycles
    └── predict/...
```

To redraw the plots of a run: `python3 -m quarch_profiler.plots runs/<run>/`

## What a measurement contains

| Field | Meaning |
|---|---|
| `label`, `repetition`, `call` | What was measured, in which repetition, which call |
| `workload_seconds` | How long your code ran |
| `window_seconds`, `n_samples` | How long the meter recorded (8,000 samples per second) |
| `joules` | Total wall energy during the recording |
| `energy_above_idle_joules` | **Energy your code used:** total − idle power × window |
| `mean_watts`, `peak_watts`, `min_watts`, `std_watts` | Power statistics |
| `baseline_watts` | The idle power that was subtracted |
| `cpu_temp_start_c`, `cpu_temp_end_c` | CPU temperature at the start and end |
| `device`, `ports` | Meter and port(s) counted |

The samples CSV has one row per 125 µs: `time_us`, `t_s`, current and voltage of
ports L1–L3 (`L1_mA`, `L1_mV`, ...), `Neutral_mA`, the power of each port (`L1_W`, ...)
and `watts`.

**Ports.** The meter has three output ports, L1, L2 and L3. Our experiment machine
is plugged into **L1**, so only L1 counts (`PORTS` in `settings.py`). L2 and L3 only
show sensor noise.

**Why power goes up and down in the plots.** Wall power is AC. Voltage and current
swing positive and negative 60 times a second, so their product rises and falls
twice per cycle. The mean over a cycle is the power, and energy is its sum over time.

## Requirements and setup

```bash
pip install quarchpy numpy pandas psutil matplotlib
```

- Python 3.10+, Linux (for the CPU temperature). Tested with quarchpy 2.2.24.
- Close **Quarch Power Studio** before a run: it runs its own QIS. The profiler
  starts QIS itself.
- Run from this folder (or put it on `PYTHONPATH`) so `python3 -m quarch_profiler`
  is found. Your file can be anywhere.
- All settings (device, ports, temperature rule, protected processes, ...) are in
  `quarch_profiler/settings.py`.

Try it: `python3 -m quarch_profiler test/example_experiment.py -n 3`

## Troubleshooting

| Message | What to do |
|---|---|
| `CPU temperature did not settle before repetition N` | Something keeps the CPU busy or warm. Look at the CPU check in `report.txt`. To loosen the rule, raise `TEMP_SPREAD_C` in `settings.py`. |
| `the script failed (exit code ...)` | Your file raised an error; it is printed above. The run stops; what was recorded is kept and plotted. |
| `not started by the runner - nothing is measured` | You ran the file directly. Use `python3 -m quarch_profiler <file>`. |
| `a Quarch recording is already running - recordings cannot nest` | A measured function was called inside another measurement. |
| `Could not find module '...' in QIS within 5s` | QIS does not see the meter. Check the USB cable and that Quarch Power Studio is closed. |
| `meter replied 'FAIL: ...'`, `no data from the meter for 10 s` | The meter is stuck. Close QIS (`python3 -c "from quarchpy.qis import closeQis; closeQis()"`), replug the meter's USB, try again. |
| A process is listed as `STILL RUNNING` / `already exited on its own` | It ignored the request to exit (close it yourself) / it quit by itself (nothing to do). |

## How the code is organised

```
quarch_profiler/
├── __main__.py           command line
├── runner.py             Runner            the steps above
├── api.py                measure, segment  what your file uses
├── recorder.py           Recorder          records one repetition into the run folder
├── segment.py            Segment           one recording
├── measurement.py        Measurement       the result of one recording
├── run_folder.py         RunFolder         the folder of one run
├── summary.py            summarize         summary.csv
├── plots.py              plot_run          all graphs
├── process_check.py      ProcessCheck      list processes, close the ones you choose
├── cpu_check.py          CpuUsageCheck     CPU usage
├── temperature_check.py  TemperatureCheck  wait until at the idle reference
├── temperature.py        CpuTemperature    reads the CPU temperature
├── meter.py              QuarchMeter       the meter, through quarchpy and QIS
├── samples.py            SampleParser      raw meter text -> samples table
├── report.py             CheckReport       the result of one check
└── settings.py           all settings
```
