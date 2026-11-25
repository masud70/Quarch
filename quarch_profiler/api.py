"""What your file uses: @measure and `with segment(...)`.

    from quarch_profiler import measure, segment

    @measure("fit")
    def train(): ...

    with segment("predict"):
        ...

Run the file with the runner (python3 -m quarch_profiler my_file.py -n 5).
Started on its own (python3 my_file.py), the file runs normally and nothing is measured.
"""

import contextlib
import functools

from .recorder import Recorder

_recorder = None
_looked_up = False


def _get_recorder():
    """The Recorder set up by the runner, or None (looked up once)."""
    global _recorder, _looked_up
    if not _looked_up:
        _looked_up = True
        _recorder = Recorder.from_environment()
        if _recorder is None:
            print("[quarch_profiler] not started by the runner - nothing is measured "
                  "(use: python3 -m quarch_profiler <file>)", flush=True)
    return _recorder


def segment(label="segment"):
    """Measure the lines inside `with segment(label):`."""
    recorder = _get_recorder()
    return recorder.segment(label) if recorder else contextlib.nullcontext()


def measure(label=None):
    """Measure every call of a function. Use as @measure or @measure("label");
    the label defaults to the function's name."""
    if callable(label):                     # used bare: @measure
        return measure()(label)

    def decorate(fn):
        name = label or fn.__name__

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with segment(name):
                return fn(*args, **kwargs)

        return wrapper

    return decorate
