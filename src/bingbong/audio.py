import shutil
import subprocess  # noqa: S404
from collections.abc import Sequence
from importlib.resources import files
from pathlib import Path

import sounddevice as sd
import soundfile as sf

from .paths import DEFAULT_OUTDIR

# --- Constants ---
DATA = files("bingbong.data")
POP = str(DATA / "pop.wav")
CHIME = str(DATA / "chime.wav")
POPS_PER_CLUSTER = 3
FFMPEG = shutil.which("ffmpeg")

POPS_PER_CLUSTER = 3


def play_file(path: Path) -> None:
    try:
        data, fs = sf.read(str(path), dtype="float32")
        sd.play(data, fs)
        sd.wait()
    except (sf.LibsndfileError, OSError, RuntimeError) as err:
        print(f"Failed to play audio: {err}")


def concat(input_files: Sequence[str], output: Path, outdir: Path = DEFAULT_OUTDIR) -> None:
    """Concatenate .wav files into one using ffmpeg."""
    outdir.mkdir(parents=True, exist_ok=True)
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


def make_quarters(outdir: Path = DEFAULT_OUTDIR) -> None:
    for n in range(1, 4):
        pops = [POP] * n
        output = outdir / f"quarter_{n}.wav"
        concat(pops, output, outdir=outdir)


def make_hours(outdir: Path = DEFAULT_OUTDIR) -> None:
    for hour in range(1, 13):
        clusters = [POP] * (hour - 1)
        output = outdir / f"hour_{hour}.wav"
        concat([CHIME, *clusters], output, outdir=outdir)


def make_silence(outdir: Path = DEFAULT_OUTDIR, duration: int = 1) -> None:
    silence_path = outdir / "silence.wav"
    subprocess.run(
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
    )  # noqa: S603


def build_all(outdir: Path = DEFAULT_OUTDIR) -> None:
    make_silence(outdir)
    make_quarters(outdir)
    make_hours(outdir)
