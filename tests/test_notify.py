import importlib
import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from freezegun import freeze_time

import bingbong.audio as audio_mod
from bingbong import audio, notify, paths
from bingbong.notify import nearest_quarter, notify_time, resolve_chime_path

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


@freeze_time("2024-01-01 15:00:00")
def test_notify_logs_time_and_file(monkeypatch, tmp_path, capsys):
    audio.build_all(tmp_path)
    monkeypatch.setattr(audio_mod, "play_file", lambda _path: None)
    notify.notify_time(outdir=tmp_path)
    captured = capsys.readouterr().out.strip()
    assert "2024-01-01T15:00:00" in captured
    assert "hour_4.wav" in captured


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


def test_notify_rebuild_fails(monkeypatch, caplog):
    monkeypatch.setattr("bingbong.notify.build_all", lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    monkeypatch.setattr("bingbong.notify.resolve_chime_path", lambda *_: Path("/nonexistent.wav"))

    with caplog.at_level(logging.ERROR):
        notify.notify_time()
    assert "Error during rebuild" in caplog.text


def test_notify_rebuild_missing_file(monkeypatch, tmp_path, caplog):
    dummy_path = tmp_path / "missing.wav"

    monkeypatch.setattr("bingbong.notify.resolve_chime_path", lambda *_: dummy_path)
    monkeypatch.setattr("bingbong.notify.build_all", lambda: None)

    with caplog.at_level(logging.ERROR):
        notify.notify_time(outdir=tmp_path)
    assert "Rebuild failed" in caplog.text


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


def test_notify_respects_manual_pause(tmp_path, monkeypatch):
    # create a pause entry in the future
    future = "2025-05-06T11:00:00"
    (tmp_path / ".state.json").write_text(json.dumps({"pause_until": future}))

    called = {"played": False}
    monkeypatch.setattr(
        audio_mod,
        "play_file",
        lambda _path: called.__setitem__("played", True),  # noqa: FBT003
    )

    # Should return early, not call play_file
    notify_time(outdir=tmp_path)
    assert not called["played"]


@freeze_time("2025-05-06 10:10:00")
def test_notify_unpauses_after_expiry(tmp_path, monkeypatch):
    # pause expired at 10:00
    (tmp_path / ".state.json").write_text(json.dumps({"pause_until": "2025-05-06T10:00:00"}))

    # dummy chime path
    dummy = tmp_path / "hour_1.wav"
    dummy.write_bytes(b"")  # exist

    # force resolve_chime_path to return our dummy
    monkeypatch.setattr("bingbong.notify.resolve_chime_path", lambda _hour, _nearest, _outdir: dummy)

    called = {"played": False}
    monkeypatch.setattr(
        audio_mod,
        "play_file",
        lambda _path: called.__setitem__("played", True),  # noqa: FBT003
    )

    notify_time(outdir=tmp_path)
    assert called["played"]
    # expired entry should be removed
    data = json.loads((tmp_path / ".state.json").read_text())
    assert "pause_until" not in data


def test_notify_respects_dnd(tmp_path, monkeypatch):
    # no pause file
    # stub subprocess.run to pretend DND is on
    class DummyCP:
        def __init__(self):
            self.stdout = "1"

    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: DummyCP())

    called = {"played": False}
    monkeypatch.setattr(
        audio_mod,
        "play_file",
        lambda _path: called.__setitem__("played", True),  # noqa: FBT003
    )

    notify_time(outdir=tmp_path)
    assert not called["played"]


def test_dnd_probe_failure(tmp_path, monkeypatch, caplog):
    audio.build_all(tmp_path)

    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/defaults")

    def fake_run(*_a, **_k):
        msg = "boom"
        raise OSError(msg)

    monkeypatch.setattr(subprocess, "run", fake_run)
    played = {"called": False}
    monkeypatch.setattr(
        audio_mod,
        "play_file",
        lambda _p: played.__setitem__("called", True),  # noqa: FBT003
    )

    with caplog.at_level(logging.WARNING):
        notify.notify_time(outdir=tmp_path)
    assert "DND check failed" in caplog.text
    assert played["called"]


@freeze_time("2024-01-01 15:00:00")
def test_on_wake_plays_missed_chimes(tmp_path, monkeypatch, capsys):
    audio.build_all(tmp_path)
    state_file = tmp_path / ".state.json"
    state_file.write_text(json.dumps({"last_run": "2024-01-01T12:00:00"}))
    played: list[str] = []
    monkeypatch.setattr("bingbong.audio.play_file", lambda p: played.append(Path(p).name))
    notify.on_wake(outdir=tmp_path)
    out = capsys.readouterr().out
    assert "hour_2.wav" in played
    assert "hour_3.wav" in played
    assert "hour_2.wav" in out
    assert "hour_3.wav" in out
    data = json.loads(state_file.read_text())
    assert data["last_run"].startswith("2024-01-01T15:00:00")


def test_policy_selection(monkeypatch, tmp_path):
    audio.build_all(tmp_path)

    class DummyPolicy:
        @staticmethod
        def resolve(_now, outdir):
            return outdir / "quarter_2.wav"

    played = {}
    monkeypatch.setattr(audio_mod, "play_file", lambda p: played.setdefault("path", p))
    notify.notify_time(outdir=tmp_path, policy=DummyPolicy())
    assert played["path"].name == "quarter_2.wav"


def test_config_reload(tmp_path, monkeypatch, caplog):
    cfg = tmp_path / "config.toml"
    cfg.write_text("a=1")
    monkeypatch.setattr(paths, "config_path", lambda: cfg)
    monkeypatch.setattr(notify, "config_path", lambda: cfg)
    notify.check_config_reload()
    time.sleep(1)
    cfg.write_text("a=2")
    orig = cfg.stat().st_mtime
    os.utime(cfg, (orig + 5, orig + 5))
    with caplog.at_level(logging.INFO, logger="bingbong.notify"):
        changed = notify.check_config_reload()
    assert changed
    assert "Configuration reload detected" in caplog.text


def test_bad_pause_file_is_deleted_and_played(tmp_path, monkeypatch):
    # create a malformed pause entry
    (tmp_path / ".state.json").write_text(json.dumps({"pause_until": "not-a-timestamp"}))

    # dummy chime path
    dummy = tmp_path / "quarter_1.wav"
    dummy.write_bytes(b"")

    monkeypatch.setattr("bingbong.notify.resolve_chime_path", lambda _hour, _nearest, _outdir: dummy)

    called = {"played": False}
    monkeypatch.setattr(
        audio_mod,
        "play_file",
        lambda _path: called.__setitem__("played", True),  # noqa: FBT003
    )

    notify_time(outdir=tmp_path)
    assert called["played"]
    # malformed entry should have been removed
    data = json.loads((tmp_path / ".state.json").read_text())
    assert "pause_until" not in data
