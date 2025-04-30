from pathlib import Path

from bingbong import audio
from bingbong.audio import play_file


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
