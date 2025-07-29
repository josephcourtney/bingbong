from bingbong.scheduler import ChimeScheduler
from bingbong.renderer import MinimalRenderer


def test_scheduler_minutes_for_chime():
    sched = ChimeScheduler(chime_schedule="*/15 * * * *")
    assert sched.minutes_for_chime() == ["0", "15", "30", "45"]


def test_scheduler_invalid_cron():
    try:
        ChimeScheduler(chime_schedule="bad cron")
    except ValueError:
        pass
    else:
        assert False, "expected ValueError"


def test_minutes_for_suppression():
    sched = ChimeScheduler(suppress_schedule=["5 * * * *", "10 * * * *"])
    assert sched.minutes_for_suppression() == ["5", "10"]


def test_minimal_renderer():
    tpl = "<plist/>"
    rend = MinimalRenderer()
    out = rend.render(["0"], ["30"], tpl)
    assert "Minute" in out and tpl in out
