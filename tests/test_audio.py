import subprocess
from pathlib import Path

import pytest

from bingbong.audio import play_once, play_repeated


def test_play_once_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "no.wav"
    with pytest.raises(SystemExit):
        play_once(missing)


def test_play_once_nonzero(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    f = tmp_path / "a.wav"
    f.write_bytes(b"0")

    class Res:
        returncode = 1

    def fake_run(*_: object, **__: object) -> Res:
        return Res()

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(SystemExit):
        play_once(f)


def test_play_repeated_calls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    f = tmp_path / "a.wav"
    f.write_bytes(b"0")
    calls: list[list[object]] = []

    class Res:
        returncode = 0

    def fake_run(*args: object, **__: object) -> Res:
        calls.append(list(args))
        return Res()

    monkeypatch.setattr(subprocess, "run", fake_run)
    play_repeated(f, 3, delay=0)
    assert len(calls) == 3
