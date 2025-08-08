import pytest

from bingbong.scheduler import ChimeScheduler, render


def test_render_chime_schedule():
    cfg = ChimeScheduler(chime_schedule="*/15 * * * *")
    sch = render(cfg)
    minutes = {entry["Minute"] for entry in sch.time.calendar_entries}
    assert minutes == {0, 15, 30, 45}
    assert all(isinstance(entry["Minute"], int) for entry in sch.time.calendar_entries)


def test_scheduler_invalid_cron():
    with pytest.raises(ValueError, match="Invalid cron expression"):
        ChimeScheduler(chime_schedule="bad cron")


def test_render_suppression():
    cfg = ChimeScheduler(suppress_schedule=["5 2 * * *"])
    sch = render(cfg)
    assert {"Hour": 2, "Minute": 5} in sch.time.calendar_entries
