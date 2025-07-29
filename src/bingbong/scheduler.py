from __future__ import annotations

from dataclasses import dataclass, field

from croniter import croniter

__all__ = ["ChimeScheduler"]


def _minutes_from_cron(expr: str) -> list[str]:
    m0 = expr.split(maxsplit=1)[0]
    if m0.startswith("*/"):
        step = int(m0[2:])
        return [str(i) for i in range(0, 60, step)]
    if "," in m0:
        return m0.split(",")
    if m0 == "*":
        return [str(i) for i in range(60)]
    return [m0]


@dataclass(slots=True)
class ChimeScheduler:
    """Manage chime and suppression schedules."""

    chime_schedule: str = "0 * * * *"
    suppress_schedule: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate cron expressions on init."""
        if not croniter.is_valid(self.chime_schedule):
            msg = "Invalid cron expression"
            raise ValueError(msg)
        for expr in self.suppress_schedule:
            if not croniter.is_valid(expr):
                msg = "Invalid cron expression"
                raise ValueError(msg)

    def minutes_for_chime(self) -> list[str]:
        """Return list of minutes when chimes should occur."""
        return _minutes_from_cron(self.chime_schedule)

    def minutes_for_suppression(self) -> list[str]:
        """Return list of minutes extracted from suppress cron expressions."""
        return [expr.split()[0] for expr in self.suppress_schedule]
