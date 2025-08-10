from __future__ import annotations

import shutil
import subprocess  # noqa: S404
from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

from .errors import BingBongError
from .paths import ensure_outdir

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["FFmpeg", "concat", "ffmpeg_available", "find_ffmpeg", "get_ffmpeg", "make_silence"]

DATA = files("bingbong.data")
POP = DATA / "pop.wav"
CHIME = DATA / "chime.wav"


def get_ffmpeg() -> FFmpeg:
    """Return an FFmpeg instance."""
    return FFmpeg()


@cache
def find_ffmpeg() -> str | None:
    """Return the path to ffmpeg or ``None`` if not found."""
    return shutil.which("ffmpeg")


def ffmpeg_available() -> bool:
    """Return True if the ffmpeg binary is on PATH."""
    return find_ffmpeg() is not None


class FFmpeg:
    binary: str | None
    """Thin wrapper around the ``ffmpeg`` binary.

    Providing a class makes it easier to inject a fake during testing and keeps
    subprocess handling isolated in one place.
    """

    def __init__(self, binary: str | None = None) -> None:
        self.binary = binary or find_ffmpeg()

    def _ensure_binary(self) -> str:
        if not self.binary:
            msg = "ffmpeg is not available"
            raise BingBongError(msg)
        return self.binary

    def run(self, args: list[str]) -> None:
        """Execute ``ffmpeg`` with ``args``.

        Separated for easier monkeypatching in tests.
        """
        _ = subprocess.run([self._ensure_binary(), *args], check=True)  # noqa: S603

    def concat(self, inputs: Sequence[Path], output: Path, outdir: Path | None = None) -> None:
        if outdir is None:
            outdir = ensure_outdir()

        list_path = outdir / "temp_list.txt"
        outdir.mkdir(parents=True, exist_ok=True)
        with list_path.open("w", encoding="utf-8") as f:
            for file in inputs:
                _ = f.write(f"file '{file}'\n")

        try:
            self.run([
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-c",
                "copy",
                str(output),
            ])
        except subprocess.CalledProcessError as e:  # pragma: no cover - passthrough
            msg = f"ffmpeg concat failed: {e}"
            raise BingBongError(msg) from e
        finally:
            list_path.unlink(missing_ok=True)

    def make_silence(self, outdir: Path | None = None, duration: int = 1) -> None:
        if outdir is None:
            outdir = ensure_outdir()
        outdir.mkdir(parents=True, exist_ok=True)

        silence_path = outdir / "silence.wav"
        self.run([
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-t",
            str(duration),
            str(silence_path),
        ])


def concat(
    inputs: Sequence[Path | str],
    output: Path,
    outdir: Path | None = None,
    *,
    runner: FFmpeg | None = None,
) -> None:
    """Concatenate ``inputs`` into ``output`` using ``ffmpeg``."""
    path_inputs = [Path(p) for p in inputs]
    (runner or get_ffmpeg()).concat(path_inputs, output, outdir)


def make_silence(
    outdir: Path | None = None,
    duration: int = 1,
    *,
    runner: FFmpeg | None = None,
) -> None:
    """Generate a silent WAV of ``duration`` seconds."""
    (runner or get_ffmpeg()).make_silence(outdir, duration)
