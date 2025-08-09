from __future__ import annotations

from dataclasses import dataclass, field

from croniter import croniter
from onginred.schedule import LaunchdSchedule

__all__ = ["ChimeScheduler", "render"]


@dataclass(slots=True)
class ChimeScheduler:
    """Manage chime and suppression schedules.

    Attributes
    ----------
    chime_schedule:
        Cron expression defining when a chime should play.
    suppress_schedule:
        Cron expressions that specify suppression windows.
    """

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


def render(cfg: ChimeScheduler) -> LaunchdSchedule:
    """Return a :class:`LaunchdSchedule` populated from ``cfg``."""
    sch = LaunchdSchedule()
    sch.add_cron(cfg.chime_schedule)
    for rng in cfg.suppress_schedule:
        minute, hour, *_ = rng.split()
        spec = f"{int(hour):02d}:{int(minute):02d}-{int(hour):02d}:{int(minute):02d}"
        sch.time.add_suppression_window(spec)
    sch.behavior.run_at_load = True
    sch.behavior.keep_alive = True
    return sch
