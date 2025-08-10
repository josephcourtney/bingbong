import pytest

from bingbong.scheduler import ChimeScheduler, render


def test_render_chime_schedule():
    cfg = ChimeScheduler()
    sch = render(cfg)
    minutes = {entry["Minute"] for entry in sch.time.calendar_entries}
    assert minutes == {0, 15, 30, 45}
    assert all(isinstance(entry["Minute"], int) for entry in sch.time.calendar_entries)


def test_render_suppression():
    cfg = ChimeScheduler(suppress_schedule=["02:05-02:10"])
    sch = render(cfg)
    entries = {(e["Hour"], e["Minute"]) for e in sch.time.calendar_entries}
    assert (2, 5) in entries
    assert (2, 10) in entries


def test_render_multiple_windows_and_overnight():
    cfg = ChimeScheduler(suppress_schedule=["08:00-09:00", "23:30-00:30"])
    sch = render(cfg)
    entries = {(e["Hour"], e["Minute"]) for e in sch.time.calendar_entries}
    assert (8, 0) in entries  # within first window
    assert (8, 59) in entries
    assert (23, 45) in entries  # second window before midnight
    assert (0, 30) in entries  # second window after midnight


def test_scheduler_invalid_window():
    with pytest.raises(ValueError, match="Invalid time range"):
        ChimeScheduler(suppress_schedule=["bad"])


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
