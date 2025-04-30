import importlib
import shutil
from pathlib import Path

import pytest
from freezegun import freeze_time

from bingbong import audio, notify, paths
from bingbong.notify import nearest_quarter, resolve_chime_path

HOURS = list(range(1, 13))
QUARTERS = [1, 2, 3]


@pytest.fixture(autouse=True)
def clean_outdir(tmp_path):
    """Ensure a clean tmp_path before each test."""
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    yield
    if tmp_path.exists():
        shutil.rmtree(tmp_path)


def test_make_silence_creates_file(tmp_path):
    audio.make_silence(tmp_path)
    assert (tmp_path / "silence.wav").exists()


def test_make_quarters_creates_expected_files(tmp_path):
    audio.make_silence(tmp_path)
    audio.make_quarters(tmp_path)
    for n in QUARTERS:
        assert (tmp_path / f"quarter_{n}.wav").exists()


def test_make_hours_creates_expected_files(tmp_path):
    audio.make_silence(tmp_path)
    audio.make_hours(tmp_path)
    for hour in HOURS:
        assert (tmp_path / f"hour_{hour}.wav").exists()


def test_build_all_creates_everything(tmp_path):
    audio.build_all(tmp_path)
    for n in QUARTERS:
        assert (tmp_path / f"quarter_{n}.wav").exists()
    for hour in HOURS:
        assert (tmp_path / f"hour_{hour}.wav").exists()
    assert (tmp_path / "silence.wav").exists()


@freeze_time("2024-01-01 15:00:00")
def test_notify_time_on_the_hour(monkeypatch, tmp_path):
    audio.build_all(tmp_path)

    called = {}
    monkeypatch.setattr("bingbong.audio.play_file", lambda path: called.setdefault("path", path))

    notify.notify_time(outdir=tmp_path)

    expected = tmp_path / "hour_4.wav"
    assert called["path"] == expected


@freeze_time("2024-01-01 10:16:00")
def test_notify_time_nearest_quarter(monkeypatch, tmp_path):
    audio.build_all(tmp_path)

    called = {}
    monkeypatch.setattr("bingbong.audio.play_file", lambda path: called.setdefault("path", path))

    notify.notify_time(outdir=tmp_path)

    expected = tmp_path / "quarter_1.wav"
    assert called["path"] == expected


@freeze_time("2024-01-01 10:44:00")
def test_notify_time_quarter_3(monkeypatch, tmp_path):
    audio.build_all(tmp_path)

    called = {}
    monkeypatch.setattr("bingbong.audio.play_file", lambda path: called.setdefault("path", path))

    notify.notify_time(outdir=tmp_path)

    expected = tmp_path / "quarter_3.wav"
    assert called["path"] == expected


@freeze_time("2024-01-01 10:00:00")
def test_notify_missing_triggers_rebuild(monkeypatch, tmp_path):
    called = {"built": False, "played": None}

    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "bingbong.notify.build_all",
        lambda outdir=tmp_path: called.__setitem__("built", True) or audio.build_all(outdir),  # noqa: FBT003
    )
    monkeypatch.setattr("bingbong.audio.play_file", lambda path: called.__setitem__("played", path))

    notify.notify_time(outdir=tmp_path)

    expected = tmp_path / "hour_11.wav"
    assert called["built"] is True
    assert called["played"] == expected


def test_notify_rebuild_fails(monkeypatch, capsys):
    monkeypatch.setattr("bingbong.notify.build_all", lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    monkeypatch.setattr("bingbong.notify.resolve_chime_path", lambda *_: Path("/nonexistent.wav"))

    notify.notify_time()

    out = capsys.readouterr().out
    assert "Error during rebuild" in out


def test_notify_rebuild_missing_file(monkeypatch, tmp_path, capsys):
    dummy_path = tmp_path / "missing.wav"

    monkeypatch.setattr("bingbong.notify.resolve_chime_path", lambda *_: dummy_path)
    monkeypatch.setattr("bingbong.notify.build_all", lambda: None)

    notify.notify_time(outdir=tmp_path)

    out = capsys.readouterr().out
    assert "Rebuild failed" in out


def test_nearest_quarter_rounding_edges():
    assert nearest_quarter(7) == 0
    assert nearest_quarter(8) == 1
    assert nearest_quarter(52) == 3
    assert nearest_quarter(53) == 0


def test_resolve_chime_path_midnight_rollover(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    importlib.reload(paths)
    monkeypatch.setattr(paths, "DEFAULT_OUTDIR", tmp_path)
    p = resolve_chime_path(12, 0)
    assert p == tmp_path / "hour_1.wav"
