from __future__ import annotations

from bingbong.service import build_schedule


def test_build_schedule_entries() -> None:
    sched = build_schedule()
    assert len(sched.time.calendar_entries) == 96
