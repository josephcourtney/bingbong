from __future__ import annotations

import sys
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

from bingbong import cli
from bingbong.config import Config

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _setup_cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BINGBONG_APP_SUPPORT", str(tmp_path))
    chime = tmp_path / "c.wav"
    pop = tmp_path / "p.wav"
    chime.write_bytes(b"0")
    pop.write_bytes(b"0")
    Config(chime, pop).save()
    monkeypatch.setattr(sys, "platform", "darwin")


def test_tick_quiet_hours(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_cfg(tmp_path, monkeypatch)
    monkeypatch.setenv("BINGBONG_QUIET_HOURS", "00:00-23:59")
    called: list[str] = []
    monkeypatch.setattr(cli, "play_once", lambda *_, **__: called.append("chime"))
    monkeypatch.setattr(cli, "play_repeated", lambda *_, **__: called.append("pop"))
    monkeypatch.setattr(cli, "compute_pop_count", lambda _m, _h: (1, True))
    assert cli.tick.callback
    cli.tick.callback()
    assert called == []


def test_tick_drift(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _setup_cfg(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "compute_pop_count", lambda _m, _h: (1, True))
    called: list[str] = []
    monkeypatch.setattr(cli, "play_once", lambda *_, **__: called.append("chime"))
    monkeypatch.setattr(cli, "play_repeated", lambda *_, **__: called.append("pop"))

    class FakeDateTime:
        def __init__(self) -> None:
            self.calls = 0

        def now(self):
            self.calls += 1
            if self.calls == 1:
                return datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
            return datetime(2024, 1, 1, 0, 1, tzinfo=UTC)

        def astimezone(self, _dt=None):
            return self.now().astimezone()

    fake_dt = FakeDateTime()
    monkeypatch.setattr(cli, "datetime", fake_dt)
    monkeypatch.setattr(cli, "time", SimpleNamespace(sleep=lambda _x: None))
    assert cli.tick.callback
    cli.tick.callback()
    assert called == ["chime"]
