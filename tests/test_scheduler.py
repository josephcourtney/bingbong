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


def test_render_behavior_options():
    cfg = ChimeScheduler(
        exit_timeout=10,
        throttle_interval=20,
        successful_exit=False,
        crashed=True,
    )
    sch = render(cfg)
    assert sch.behavior.exit_timeout == 10
    assert sch.behavior.throttle_interval == 20
    assert sch.behavior.successful_exit is False
    assert sch.behavior.crashed is True


def test_render_adds_watch_and_wake(monkeypatch, tmp_path):
    monkeypatch.setattr("bingbong.scheduler.config_path", lambda: tmp_path / "config.toml")
    sch = render(ChimeScheduler())
    assert str(tmp_path / "config.toml") in sch.fs.watch_paths
    assert sch.events.launch_events["com.apple.iokit.matching"]["SystemWake"] == {
        "IOServiceClass": "IOPMrootDomain"
    }
