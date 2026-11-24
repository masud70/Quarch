"""Measuring a function: `@profiler.measure(...)`."""

import functools
import types

from .measurement import MeasurementLog


class MeasuredFunction:
    """A function whose every call is recorded. Made by QuarchProfiler.measure().

        @profiler.measure("fit")
        def train(X, y): ...

        train(X, y)                  # returns what the function returns
        train.last                   # Measurement of the newest call
        train.measurements           # MeasurementLog of every call
        train.measurements.to_frame()

    Also works on methods inside a class.
    """

    def __init__(self, fn, profiler, label=None, record_args=False, **options):
        functools.update_wrapper(self, fn)
        self.fn = fn
        self.profiler = profiler
        self.label = label or fn.__qualname__
        self.record_args = record_args
        self.options = options              # override the profiler's defaults
        self.measurements = MeasurementLog()

    @property
    def last(self):
        return self.measurements.last

    def __call__(self, *args, **kwargs):
        with self.profiler.segment(self.label, extra=self._extra(args, kwargs),
                                   **self.options) as seg:
            value = self.fn(*args, **kwargs)
        self.measurements.append(seg.result)
        return value

    def __get__(self, instance, owner):
        """Used as a method: bind to the instance, like a plain function would."""
        if instance is None:
            return self
        return types.MethodType(self, instance)

    def _extra(self, args, kwargs):
        extra = {"function": f"{self.fn.__module__}.{self.fn.__qualname__}",
                 "call_index": len(self.measurements) + 1}
        if self.record_args:
            extra["args"] = [repr(a) for a in args]
            extra["kwargs"] = {k: repr(v) for k, v in kwargs.items()}
        return extra
