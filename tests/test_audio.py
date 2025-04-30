from pathlib import Path

from bingbong import audio
from bingbong.audio import play_file

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


def test_play_file_success(monkeypatch, tmp_path):
    dummy_wav = tmp_path / "good.wav"
    dummy_wav.write_bytes(b"\0" * 44)  # fake minimal WAV header

    monkeypatch.setattr("bingbong.audio.sf.read", lambda *_a, **_k: ([0.0], 44100))
    monkeypatch.setattr("bingbong.audio.sd.play", lambda _data, _fs: None)
    monkeypatch.setattr("bingbong.audio.sd.wait", lambda: None)

    audio.play_file(dummy_wav)
