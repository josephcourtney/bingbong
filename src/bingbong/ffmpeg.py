from __future__ import annotations

import shutil
import subprocess  # noqa: S404
from functools import cache
from importlib.resources import files
from typing import TYPE_CHECKING

from .paths import ensure_outdir

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["concat", "ffmpeg_available", "find_ffmpeg", "make_silence"]

DATA = files("bingbong.data")
POP = str(DATA / "pop.wav")
CHIME = str(DATA / "chime.wav")


@cache
def find_ffmpeg() -> str | None:
    """Return the path to ffmpeg or ``None`` if not found."""
    return shutil.which("ffmpeg")


def ffmpeg_available() -> bool:
    """Return True if the ffmpeg binary is on PATH."""
    return find_ffmpeg() is not None


def concat(inputs: list[Path], output: Path, outdir: Path | None = None) -> None:
    """Concatenate .wav files into one using ffmpeg."""
    if not ffmpeg_available():
        msg = "ffmpeg is not available"
        raise RuntimeError(msg)
    if outdir is None:
        outdir = ensure_outdir()

    list_path = outdir / "temp_list.txt"
    outdir.mkdir(parents=True, exist_ok=True)
    with list_path.open("w", encoding="utf-8") as f:
        for file in inputs:
            f.write(f"file '{file}'\n")

    ffmpeg_bin = find_ffmpeg()
    if not ffmpeg_bin:
        msg = "ffmpeg is not available on this system."
        raise RuntimeError(msg)

    try:
        subprocess.run(  # noqa: S603
            [
                ffmpeg_bin,
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
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        msg = f"ffmpeg concat failed: {e}"
        raise RuntimeError(msg) from e
    finally:
        list_path.unlink(missing_ok=True)


def make_silence(outdir: Path | None = None, duration: int = 1) -> None:
    """Generate a silent WAV of given duration."""
    if not ffmpeg_available():
        msg = "ffmpeg is not available"
        raise RuntimeError(msg)
    if outdir is None:
        outdir = ensure_outdir()
    outdir.mkdir(parents=True, exist_ok=True)

    silence_path = outdir / "silence.wav"
    ffmpeg_bin = find_ffmpeg()
    if not ffmpeg_bin:
        msg = "ffmpeg is not available on this system."
        raise RuntimeError(msg)

    subprocess.run(  # noqa: S603
        [
            ffmpeg_bin,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-t",
            str(duration),
            str(silence_path),
        ],
        check=True,
    )
