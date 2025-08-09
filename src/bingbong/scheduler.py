from __future__ import annotations

from dataclasses import dataclass, field

from croniter import croniter
from onginred.schedule import LaunchdSchedule

from .paths import config_path

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
    exit_timeout: int | None = None
    throttle_interval: int | None = None
    successful_exit: bool | None = None
    crashed: bool | None = None

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
    sch.add_watch_path(str(config_path()))
    sch.add_launch_event("com.apple.iokit.matching", "SystemWake", {"IOServiceClass": "IOPMrootDomain"})
    for rng in cfg.suppress_schedule:
        minute, hour, *_ = rng.split()
        spec = f"{int(hour):02d}:{int(minute):02d}-{int(hour):02d}:{int(minute):02d}"
        sch.time.add_suppression_window(spec)
    sch.behavior.run_at_load = True
    sch.behavior.keep_alive = True
    if cfg.exit_timeout is not None:
        sch.behavior.exit_timeout = cfg.exit_timeout
    if cfg.throttle_interval is not None:
        sch.behavior.throttle_interval = cfg.throttle_interval
    if cfg.successful_exit is not None:
        sch.behavior.successful_exit = cfg.successful_exit
    if cfg.crashed is not None:
        sch.behavior.crashed = cfg.crashed
    return sch
