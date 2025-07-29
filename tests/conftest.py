import subprocess
import sys
import types
from pathlib import Path

import pytest

MAX_OUTPUT_LINES = 32

# Provide dummy sounddevice/soundfile modules so tests don't require system libs
sys.modules["sounddevice"] = types.SimpleNamespace(play=lambda *_a, **_k: None, wait=lambda: None)
sys.modules["soundfile"] = types.SimpleNamespace(read=lambda *_a, **_k: ([], 44100))


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


@pytest.fixture(autouse=True)
def patch_ffmpeg(monkeypatch):
    monkeypatch.setattr("bingbong.ffmpeg.find_ffmpeg", lambda: "/usr/bin/ffmpeg")

    def fake_run(args, **_kwargs):
        # Detect silence creation
        if any("anullsrc" in arg for arg in args):
            path = Path(args[-1])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

        # Detect concat output
        if "-f" in args and "concat" in args and "-i" in args:
            output_index = args.index("-c") + 2
            output_path = Path(args[output_index])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.touch()

        class Result:
            returncode = 0
            stdout = "Usage: bingbong"
            stderr = ""

        return Result()

    monkeypatch.setattr(subprocess, "run", fake_run)
