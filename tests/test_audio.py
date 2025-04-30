import importlib
import shutil
import subprocess
from pathlib import Path

import pytest

from bingbong import audio, paths
from bingbong.audio import concat, make_silence, play_file

HOURS = list(range(1, 13))
QUARTERS = [1, 2, 3]


def test_play_file_missing_path(capsys):
    play_file(Path("/nonexistent/file.wav"))
    out = capsys.readouterr().out
    assert "Failed to play audio" in out


def test_play_file_exception(monkeypatch, tmp_path, capsys):
    dummy_file = tmp_path / "bad.wav"
    dummy_file.write_text("not really wav data")

    # Patch soundfile.read to raise an error
    def fake_read(_path, dtype=None):  # noqa: ARG001
        msg = "bad format"
        raise RuntimeError(msg)

    monkeypatch.setattr(audio.sf, "read", fake_read)

    audio.play_file(dummy_file)

    out = capsys.readouterr().out
    assert "Failed to play audio" in out


def test_concat_ffmpeg_missing(monkeypatch, tmp_path):
    # If FFMPEG is None, concat should fail immediately
    monkeypatch.setattr(audio, "FFMPEG", None)
    with pytest.raises(RuntimeError):
        concat([], tmp_path / "out.wav")


def test_make_silence_subprocess_failure(monkeypatch, tmp_path):
    # Simulate ffmpeg subprocess.run failure in make_silence()
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    importlib.reload(paths)
    # Point FFMPEG at something so list file is created, but fail the run
    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/ffmpeg")

    def fake_run(args, check):  # noqa: ARG001
        raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(audio.subprocess, "run", fake_run)
    with pytest.raises(subprocess.CalledProcessError):
        make_silence()


def test_make_silence_creates_file(tmp_path):
    audio.make_silence(tmp_path)
    silence_path = tmp_path / "silence.wav"
    assert silence_path.exists()


def test_make_quarters_creates_expected_files(tmp_path):
    audio.make_silence(tmp_path)
    audio.make_quarters(tmp_path)
    for n in QUARTERS:
        path = tmp_path / f"quarter_{n}.wav"
        assert path.exists()


def test_make_hours_creates_expected_files(tmp_path):
    audio.make_silence(tmp_path)
    audio.make_hours(tmp_path)
    for hour in HOURS:
        path = tmp_path / f"hour_{hour}.wav"
        assert path.exists()


def test_build_all_creates_everything(tmp_path):
    audio.build_all(tmp_path)

    for n in QUARTERS:
        assert (tmp_path / f"quarter_{n}.wav").exists()

    for hour in HOURS:
        assert (tmp_path / f"hour_{hour}.wav").exists()

    assert (tmp_path / "silence.wav").exists()
