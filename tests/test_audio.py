from pathlib import Path

import simpleaudio as sa

from bingbong.audio import play_file


def test_play_file_missing_path(capsys):
    play_file(Path("/nonexistent/file.wav"))
    out = capsys.readouterr().out
    assert "does not exist" in out


def test_play_file_exception(monkeypatch, tmp_path, capsys):
    dummy_file = tmp_path / "bad.wav"
    dummy_file.write_text("not really wav data")

    def fake_from_wave_file(_):
        msg = "bad format"
        raise RuntimeError(msg)

    monkeypatch.setattr(sa.WaveObject, "from_wave_file", fake_from_wave_file)
    play_file(dummy_file)

    out = capsys.readouterr().out
    assert "Failed to play audio" in out
