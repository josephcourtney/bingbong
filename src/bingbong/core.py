from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from bingbong.config import app_support, silence_path
from bingbong.constants import QUARTER_1, QUARTER_2, QUARTER_3


def get_silence_until() -> datetime | None:
    path = silence_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ts = data.get("until_epoch")
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts, tz=UTC)

    except (OSError, ValueError, json.JSONDecodeError):
        # Corrupt file or unreadable — ignore it.
        return None
    return None


def set_silence_for(minutes: int) -> datetime:
    app_dir = app_support()
    app_dir.mkdir(parents=True, exist_ok=True)
    until = datetime.now(UTC) + timedelta(minutes=minutes)

    silence_path().write_text(json.dumps({"until_epoch": until.timestamp()}, indent=2), encoding="utf-8")
    return until


def silence_active(now: datetime | None = None) -> bool:
    until = get_silence_until()
    if not until:
        return False
    now = now or datetime.now(UTC)
    return now < until


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
    return quarter_map.get(minute, (0, False))
