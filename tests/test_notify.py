import shutil
from pathlib import Path

import pytest
from freezegun import freeze_time

from bingbong import audio, notify
from bingbong.paths import OUTDIR

HOURS = list(range(1, 13))
QUARTERS = [1, 2, 3]


@pytest.fixture(autouse=True)
def clean_outdir():
    """Ensure a clean OUTDIR before each test."""
    if OUTDIR.exists():
        shutil.rmtree(OUTDIR)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    yield
    if OUTDIR.exists():
        shutil.rmtree(OUTDIR)


def test_make_silence_creates_file():
    audio.make_silence()
    silence_path = OUTDIR / "silence.wav"
    assert silence_path.exists()


def test_make_quarters_creates_expected_files():
    audio.make_silence()  # Required by make_quarters
    audio.make_quarters()
    for n in QUARTERS:
        path = OUTDIR / f"quarter_{n}.wav"
        assert path.exists(), f"Expected {path} to exist"


def test_make_hours_creates_expected_files():
    audio.make_silence()  # Required by make_hours
    audio.make_hours()
    for hour in HOURS:
        path = OUTDIR / f"hour_{hour}.wav"
        assert path.exists(), f"Expected {path} to exist"


def test_build_all_creates_everything():
    audio.build_all()

    for n in QUARTERS:
        assert (OUTDIR / f"quarter_{n}.wav").exists()

    for hour in HOURS:
        assert (OUTDIR / f"hour_{hour}.wav").exists()

    assert (OUTDIR / "silence.wav").exists()


@freeze_time("2024-01-01 15:00:00")
def test_notify_time_on_the_hour(monkeypatch):
    audio.build_all()

    called = {}

    def fake_play(path):
        called["path"] = path

    monkeypatch.setattr("bingbong.notify.play_file", fake_play)

    notify.notify_time()

    expected = OUTDIR / "hour_4.wav"  # 15:00 rounds to hour 4
    assert "path" in called
    assert called["path"] == expected


@freeze_time("2024-01-01 10:16:00")
def test_notify_time_nearest_quarter(monkeypatch):
    audio.build_all()

    called = {}

    def fake_play(path):
        called["path"] = path

    monkeypatch.setattr("bingbong.notify.play_file", fake_play)

    notify.notify_time()

    expected = OUTDIR / "quarter_1.wav"
    assert "path" in called
    assert called["path"] == expected


@freeze_time("2024-01-01 10:44:00")
def test_notify_time_quarter_3(monkeypatch):
    audio.build_all()

    called = {}

    def fake_play(path):
        called["path"] = path

    monkeypatch.setattr("bingbong.notify.play_file", fake_play)

    notify.notify_time()

    expected = OUTDIR / "quarter_3.wav"
    assert called["path"] == expected


@freeze_time("2024-01-01 10:00:00")
def test_notify_missing_triggers_rebuild(monkeypatch):
    called = {"built": False, "played": None}

    # Remove all files to simulate missing chimes
    if OUTDIR.exists():
        shutil.rmtree(OUTDIR)
    OUTDIR.mkdir(parents=True, exist_ok=True)

    def fake_build():
        called["built"] = True
        audio.build_all()

    def fake_play(path):
        called["played"] = path

    monkeypatch.setattr("bingbong.notify.build_all", fake_build)
    monkeypatch.setattr("bingbong.notify.play_file", fake_play)

    notify.notify_time()

    expected = OUTDIR / "hour_11.wav"
    assert called["built"] is True
    assert called["played"] == expected


def test_notify_rebuild_fails(monkeypatch, capsys):
    def broken_build_all():
        msg = "fail"
        raise RuntimeError(msg)

    monkeypatch.setattr("bingbong.notify.build_all", broken_build_all)
    monkeypatch.setattr("bingbong.notify.play_file", lambda _path: None)
    monkeypatch.setattr(
        "bingbong.notify.resolve_chime_path", lambda _hour, _quarter: Path("/nonexistent.wav")
    )

    notify.notify_time()

    output = capsys.readouterr().out
    assert "Error during rebuild" in output


def test_notify_rebuild_missing_file(monkeypatch, tmp_path, capsys):
    dummy_path = tmp_path / "missing.wav"

    monkeypatch.setattr("bingbong.notify.resolve_chime_path", lambda _h, _q: dummy_path)
    monkeypatch.setattr("bingbong.notify.build_all", lambda: None)
    monkeypatch.setattr("bingbong.notify.play_file", lambda _path: None)

    notify.notify_time()

    output = capsys.readouterr().out
    assert "Rebuild failed" in output
