import logging
import types
from pathlib import Path

from bingbong import audio
from bingbong.audio import play_file

HOURS = list(range(1, 13))
QUARTERS = [1, 2, 3]


def test_play_file_missing_path(caplog):
    with caplog.at_level(logging.ERROR):
        play_file(Path("/nonexistent/file.wav"))
    assert "Failed to play audio" in caplog.text
    assert "file not found" in caplog.text


def test_play_file_exception(monkeypatch, tmp_path, caplog):
    dummy_file = tmp_path / "bad.wav"
    dummy_file.write_text("not really wav data")

    # Patch simpleaudio to raise when reading file
    class Boom:
        @staticmethod
        def from_wave_file(_p):
            msg = "bad format"
            raise RuntimeError(msg)

    monkeypatch.setattr(audio.sa, "WaveObject", types.SimpleNamespace(from_wave_file=Boom.from_wave_file))

    with caplog.at_level(logging.ERROR):
        audio.play_file(dummy_file)
    assert "Failed to play audio" in caplog.text


def test_play_file_too_large(tmp_path, caplog):
    big = tmp_path / "big.wav"
    big.write_bytes(b"0" * (audio.MAX_PLAY_BYTES + 1))
    with caplog.at_level(logging.ERROR):
        play_file(big)
    assert "file too large" in caplog.text


def test_play_file_handles_small_wav(tmp_path):
    # Minimal WAV header; playback is stubbed by conftest
    dummy = tmp_path / "ok.wav"
    dummy.write_bytes(b"\0" * 44)
    play_file(dummy)


def test_build_all_creates_everything(tmp_path):
    audio.build_all(tmp_path)

    for n in QUARTERS:
        assert (tmp_path / f"quarter_{n}.wav").exists()

    for hour in HOURS:
        assert (tmp_path / f"hour_{hour}.wav").exists()

    assert (tmp_path / "silence.wav").exists()


def test_play_file_success(tmp_path):
    dummy_wav = tmp_path / "good.wav"
    dummy_wav.write_bytes(b"\0" * 44)  # fake minimal WAV header
    audio.play_file(dummy_wav)


def test_duck_others_logs(caplog):
    with caplog.at_level(logging.DEBUG):
        audio.duck_others()
    assert "duck_others() noop" in caplog.text
