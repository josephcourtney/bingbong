import shutil
import subprocess  # noqa: S404
from collections.abc import Sequence
from importlib.resources import files
from pathlib import Path

from .paths import ensure_outdir

# --- Constants ---
DATA = files("bingbong.data")
POP = str(DATA / "pop.wav")
CHIME = str(DATA / "chime.wav")

FFMPEG = shutil.which("ffmpeg")


def ffmpeg_available() -> bool:
    return FFMPEG is not None


def concat(input_files: Sequence[str], output: Path, outdir: Path | None = None) -> None:
    """Concatenate .wav files into one using ffmpeg."""
    if outdir is None:
        outdir = ensure_outdir()
    list_path = outdir / "temp_list.txt"
    with list_path.open("w", encoding="utf-8") as f:
        f.writelines(f"file '{file}'\n" for file in input_files)

    if not FFMPEG:
        msg = "ffmpeg is not available on this system."
        raise RuntimeError(msg)
    try:
        subprocess.run(  # noqa: S603
            [
                FFMPEG,
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
    finally:
        list_path.unlink(missing_ok=True)


def make_silence(outdir: Path | None = None, duration: int = 1) -> None:
    if outdir is None:
        outdir = ensure_outdir()
    silence_path = outdir / "silence.wav"
    if not FFMPEG:
        msg = "ffmpeg is not available on this system."
        raise RuntimeError(msg)
    subprocess.run(  # noqa: S603
        [
            FFMPEG,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-t",
            str(duration),  # <-- ADD THIS
            str(silence_path),
        ],
        check=True,
    )
