from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from bingbong.config import app_support, silence_path
from bingbong.constants import QUARTER_1, QUARTER_2, QUARTER_3
from bingbong.log import debug

__all__ = [
    "compute_pop_count",
    "get_silence_until",
    "set_silence_for",
    "silence_active",
]


def get_silence_until() -> datetime | None:
    path = silence_path()
    if not path.exists():
        debug("silence file not found")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ts = data.get("until_epoch")
        if isinstance(ts, (int, float)):
            until = datetime.fromtimestamp(ts, tz=UTC)
            debug(f"silence until loaded: {until.isoformat()}")
            return until

    except (OSError, ValueError, json.JSONDecodeError):
        # Corrupt file or unreadable — ignore it.
        debug("silence file unreadable or corrupt; ignoring")
        return None
    return None


def set_silence_for(minutes: int) -> datetime:
    app_dir = app_support()
    app_dir.mkdir(parents=True, exist_ok=True)
    until = datetime.now(UTC) + timedelta(minutes=minutes)

    silence_path().write_text(json.dumps({"until_epoch": until.timestamp()}, indent=2), encoding="utf-8")
    debug(f"silence set for {minutes} minutes (until {until.isoformat()})")
    return until


def silence_active(now: datetime | None = None) -> bool:
    until = get_silence_until()
    if not until:
        debug("silence inactive")
        return False
    now = now or datetime.now(UTC)
    active = now < until
    debug(f"silence active? {active} (now={now.isoformat()} until={until.isoformat()})")
    return active


def compute_pop_count(minute: int, hour_24: int) -> tuple[int, bool]:
    """Return `(pop_count, do_chime_first)`.

    - On the hour: chime first, then 1..12 pops for the hour.


    - :15 -> 1 pop, :30 -> 2 pops, :45 -> 3 pops.
    - Otherwise -> (0, False).
    """
    quarter_map = {
        0: (hour_24 % 12 or 12, True),
        QUARTER_1: (1, False),
        QUARTER_2: (2, False),
        QUARTER_3: (3, False),
    }
    res = quarter_map.get(minute, (0, False))
    debug(f"compute_pop_count(minute={minute}, hour={hour_24}) -> {res}")
    return res
