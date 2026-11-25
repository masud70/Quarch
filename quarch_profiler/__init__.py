"""Wall energy (Quarch meter) of the functions and code blocks in your file.

In your file:

    from quarch_profiler import measure, segment

    @measure("fit")
    def train(): ...

    with segment("predict"):
        ...

Run it:

    python3 -m quarch_profiler my_file.py -n 5

Everything goes to runs/<date>_<time>_my_file/. See README.md.

Files:
    __main__.py           command line
    runner.py             Runner           - checks, repetitions, summary, plots
    api.py                measure, segment - what your file uses
    recorder.py           Recorder         - records one repetition into the run folder
    segment.py            Segment          - one recording
    measurement.py        Measurement      - the result of one recording
    run_folder.py         RunFolder        - the folder of one run
    summary.py            summarize        - summary.csv
    plots.py              plot_run         - all graphs
    process_check.py      ProcessCheck     - list processes, close the ones you choose
    cpu_check.py          CpuUsageCheck    - CPU usage
    temperature_check.py  TemperatureCheck - wait until the temperature is at its idle reference
    temperature.py        CpuTemperature   - reads the CPU temperature
    meter.py              QuarchMeter      - the meter, through quarchpy
    samples.py            SampleParser     - raw meter text -> samples table
    report.py             CheckReport      - the result of one check
    settings.py           all settings
"""

from .api import measure, segment

__all__ = ["measure", "segment"]
