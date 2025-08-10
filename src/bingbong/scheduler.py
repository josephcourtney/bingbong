from __future__ import annotations

import re
from dataclasses import dataclass, field

from onginred.schedule import LaunchdSchedule

from .paths import config_path

__all__ = ["ChimeScheduler", "render"]


@dataclass(slots=True)
class ChimeScheduler:
    """Manage chime and suppression schedules.

    Attributes
    ----------
    suppress_schedule:
        Human-readable suppression windows in ``HH:MM-HH:MM`` format.
    """

    suppress_schedule: list[str] = field(default_factory=list)
    exit_timeout: int | None = None
    throttle_interval: int | None = None
    successful_exit: bool | None = None
    crashed: bool | None = None

    def __post_init__(self) -> None:
        """Validate schedules on init."""
        for expr in self.suppress_schedule:
            _parse_window(expr)  # validates format


def render(cfg: ChimeScheduler) -> LaunchdSchedule:
    """Return a :class:`LaunchdSchedule` populated from ``cfg``."""
    sch = LaunchdSchedule()

    # Quarter-hour schedule (every hour at 00/15/30/45) — include Hour+Minute so
    # all entries have both keys (tests iterate over both).
    for hour in range(24):
        for minute in (0, 15, 30, 45):
            sch.time.calendar_entries.append({"Hour": hour, "Minute": minute})

    sch.add_watch_path(str(config_path()))
    sch.add_launch_event("com.apple.iokit.matching", "SystemWake", {"IOServiceClass": "IOPMrootDomain"})
    for rng in cfg.suppress_schedule:
        sch.time.add_suppression_window(_parse_window(rng))
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


_WINDOW_RE = re.compile(r"^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$")
_HOURS_PER_DAY = 24
_MINUTES_PER_HOUR = 60


def _parse_window(rng: str) -> str:
    """Normalize a suppression window string.

    Parameters
    ----------
    rng:
        A string in ``HH:MM-HH:MM`` format. Whitespace is tolerated.

    Returns
    -------
    str
        Normalized ``HH:MM-HH:MM`` spec suitable for ``add_suppression_window``.

    Raises
    ------
    ValueError
        If ``rng`` is malformed or out of range.
    """
    match = _WINDOW_RE.match(rng.strip())
    if not match:
        msg = "Invalid time range"
        raise ValueError(msg)
    sh, sm, eh, em = map(int, match.groups())
    if not (
        0 <= sh < _HOURS_PER_DAY
        and 0 <= eh < _HOURS_PER_DAY
        and 0 <= sm < _MINUTES_PER_HOUR
        and 0 <= em < _MINUTES_PER_HOUR
    ):
        msg = "Invalid time range"
        raise ValueError(msg)
    return f"{sh:02d}:{sm:02d}-{eh:02d}:{em:02d}"
