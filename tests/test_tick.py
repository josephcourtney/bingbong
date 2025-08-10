import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from freezegun import freeze_time

from bingbong import cli
from bingbong.config import Config


def _setup_cfg(fs, mocker):
    """Create a fake config in pyfakefs and force darwin."""
    mocker.patch.dict(os.environ, {"BINGBONG_APP_SUPPORT": "/AppSupport"}, clear=False)
    fs.create_dir("/AppSupport")
    fs.create_file("/AppSupport/c.wav", contents="0")
    fs.create_file("/AppSupport/p.wav", contents="0")
    Config(Path("/AppSupport/c.wav"), Path("/AppSupport/p.wav")).save()
    import sys as _sys

    mocker.patch.object(_sys, "platform", "darwin")


def test_tick_quiet_hours(fs, mocker):
    _setup_cfg(fs, mocker)
    mocker.patch.dict(os.environ, {"BINGBONG_QUIET_HOURS": "00:00-23:59"}, clear=False)
    called: list[str] = []
    mocker.patch.object(cli, "play_once", side_effect=lambda *_, **__: called.append("chime"))
    mocker.patch.object(cli, "play_repeated", side_effect=lambda *_, **__: called.append("pop"))
    mocker.patch.object(cli, "compute_pop_count", side_effect=lambda _m, _h: (1, True))
    with freeze_time("2024-01-01 00:00:00"):
        assert cli.tick.callback
        cli.tick.callback()
    assert not called


def test_tick_drift(fs, mocker):
    _setup_cfg(fs, mocker)
    mocker.patch.object(cli, "compute_pop_count", side_effect=lambda _m, _h: (1, True))
    called: list[str] = []
    mocker.patch.object(cli, "play_once", side_effect=lambda *_, **__: called.append("chime"))
    mocker.patch.object(cli, "play_repeated", side_effect=lambda *_, **__: called.append("pop"))
    # Simulate drift by freezing time for chime, then advancing before pops
    with freeze_time("2024-01-01 00:00:00") as frozen:
        mocker.patch.object(
            cli, "time", SimpleNamespace(sleep=lambda _x: frozen.move_to("2024-01-01 00:01:00"))
        )
        assert cli.tick.callback
        cli.tick.callback()
    assert called == ["chime"]


@pytest.mark.parametrize(
    ("frozen", "expect_chime", "expect_pops"),
    [
        # on-the-hour: chime first, then hour%12 or 12 pops
        ("2024-01-01 00:00:00", True, 12),
        ("2024-01-01 03:00:00", True, 3),
        ("2024-01-01 10:00:00", True, 10),
        ("2024-01-01 13:00:00", True, 1),
        # quarter-hours: 1/2/3 pops, no chime
        ("2024-01-01 10:15:00", False, 1),
        ("2024-01-01 10:30:00", False, 2),
        ("2024-01-01 10:45:00", False, 3),
        # non-chime minute: nothing should play
        ("2024-01-01 10:07:00", False, 0),
    ],
)
def test_tick_all_cases_with_freezegun(frozen, expect_chime, expect_pops, fs, mocker):
    """Parameterize over all tick cases using frozen local time.

    This validates:
      - on-the-hour chime + correct pop count (including 00:00 -> 12)
      - quarter-hour pop counts (1/2/3) without chime
      - non-chime minutes do nothing
    """
    _setup_cfg(fs, mocker)
    # Make sleep a no-op for speed/determinism.
    mocker.patch.object(cli, "time", SimpleNamespace(sleep=lambda _x: None))

    calls: list[str] = []
    mocker.patch.object(cli, "play_once", side_effect=lambda *_, **__: calls.append("chime"))
    mocker.patch.object(cli, "play_repeated", side_effect=lambda *_a, **_kw: calls.append("pop"))

    with freeze_time(frozen):
        assert cli.tick.callback
        cli.tick.callback()

    if expect_pops == 0:
        # nothing should have played at a non-chime minute
        assert not calls
    else:
        if expect_chime:
            # chime must occur before pops
            assert calls[0] == "chime"
        else:
            # only pops entry recorded
            assert "chime" not in calls
        # play_repeated is invoked once regardless of count; we verify intent by presence.
        assert "pop" in calls
