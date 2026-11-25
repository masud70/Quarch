"""The report one check produces."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CheckReport:
    """Result of one check (CPU, temperature, processes).

    name        "cpu", "temperature" or "processes"
    passed      True / False, or None when the check only reports
    data        every number the check collected (saved as JSON)
    lines       the human-readable report (printed and saved to report.txt)
    """

    name: str
    passed: bool | None = None
    data: dict = field(default_factory=dict)
    lines: list = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    @property
    def text(self):
        title = f"== {self.name.upper()} CHECK ({self.started_at}) "
        return "\n".join([title.ljust(70, "="), *self.lines])

    def to_dict(self):
        return {"name": self.name, "started_at": self.started_at, "passed": self.passed,
                **self.data}
