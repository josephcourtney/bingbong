import importlib
import shutil
import subprocess

import pytest

from bingbong import audio, ffmpeg, paths
from bingbong.audio import concat, make_silence
from bingbong.errors import BingBongError


def test_concat_ffmpeg_missing(monkeypatch, tmp_path):
    # If FFMPEG is None, concat should fail immediately
    monkeypatch.setattr(ffmpeg, "find_ffmpeg", lambda: None)
    with pytest.raises(BingBongError):
        concat([], tmp_path / "out.wav")


def test_make_silence_subprocess_failure(monkeypatch, tmp_path):
    # Simulate ffmpeg subprocess.run failure in make_silence()
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    importlib.reload(paths)
    # Point FFMPEG at something so list file is created, but fail the run
    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/ffmpeg")

    def fake_run(args, check):
        raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr("bingbong.ffmpeg.subprocess.run", fake_run)
    with pytest.raises(subprocess.CalledProcessError):
        make_silence()


def test_make_silence_creates_file(tmp_path):
    audio.make_silence(tmp_path)
    silence_path = tmp_path / "silence.wav"
    assert silence_path.exists()


def test_concat_runtime_error(monkeypatch, tmp_path):
    monkeypatch.setattr("bingbong.ffmpeg.find_ffmpeg", lambda: None)
    with pytest.raises(BingBongError, match="ffmpeg is not available"):
        ffmpeg.concat(["a.wav", "b.wav"], tmp_path / "out.wav")


def test_make_silence_missing_ffmpeg(monkeypatch, tmp_path):
    monkeypatch.setattr("bingbong.ffmpeg.find_ffmpeg", lambda: None)
    with pytest.raises(BingBongError, match="ffmpeg is not available"):
        ffmpeg.make_silence(tmp_path)
