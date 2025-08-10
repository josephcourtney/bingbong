import sys
import types
from pathlib import Path

import pytest

MAX_OUTPUT_LINES = 32


# ----- stub simpleaudio (module) -----
simpleaudio_stub = types.ModuleType("simpleaudio")


class _BB_DummyPlay:  # noqa: N801
    def wait_done(self):  # noqa: PLR6301
        return


class _BB_DummyWave:  # noqa: N801
    def play(self):  # noqa: PLR6301
        return _BB_DummyPlay()


def _bb_from_wave_file(_p):
    return _BB_DummyWave()


WaveObject = type("WaveObject", (), {"from_wave_file": staticmethod(_bb_from_wave_file)})
simpleaudio_stub.WaveObject = WaveObject  # type: ignore[attr-defined]
sys.modules["simpleaudio"] = simpleaudio_stub


# Stub pydub so tests don't need real ffmpeg decoding
class _DummySeg:
    def __init__(self, duration: int = 0):
        self.duration = duration

    # concatenate (append)
    def __add__(self, other):
        return _DummySeg(self.duration + getattr(other, "duration", 0))

    # repeat
    def __mul__(self, n: int):  # noqa: ANN204
        return _DummySeg(self.duration * int(n))

    # export just creates a file
    def export(self, out_path, format="wav"):  # noqa: A002, ARG002, PLR6301
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        # minimal placeholder bytes
        p.write_bytes(b"\0" * 44)
        return p


# Create a real module object with an AudioSegment symbol
pydub_stub = types.ModuleType("pydub")


class _BB_AudioSegment:  # noqa: N801
    @staticmethod
    def from_file(_p):
        return _DummySeg(1000)

    @staticmethod
    def silent(duration=0):
        return _DummySeg(duration)


pydub_stub.AudioSegment = _BB_AudioSegment  # type: ignore[attr-defined]
sys.modules["pydub"] = pydub_stub


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Limit captured output per test."""
    # Only modify output for the call phase (i.e. test execution)
    if report.when == "call" and report.failed:
        new_sections: list[tuple[str, str]] = []
        for title, content in report.sections:
            if title.startswith(("Captured stdout", "Captured stderr")):
                lines = content.splitlines()
                if len(lines) > MAX_OUTPUT_LINES:
                    truncated_section: str = "\n".join([*lines[:MAX_OUTPUT_LINES], "... [output truncated]"])
                    new_sections.append((title, truncated_section))
                else:
                    new_sections.append((title, content))

            else:
                new_sections.append((title, content))
        report.sections = new_sections


@pytest.fixture
def patch_play_file(monkeypatch):
    monkeypatch.setattr("bingbong.audio.play_file", lambda _path: None)
