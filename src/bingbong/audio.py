import shutil
import subprocess  # noqa: S404
from collections.abc import Sequence
from importlib.resources import files
from pathlib import Path

import sounddevice as sd
import soundfile as sf

from .paths import OUTDIR

# --- Constants ---
DATA = files("bingbong.data")
POP = str(DATA / "pop.wav")
CHIME = str(DATA / "chime.wav")
SILENCE = str(OUTDIR / "silence.wav")
POPS_PER_CLUSTER = 3
FFMPEG = shutil.which("ffmpeg")


def play_file(path: Path) -> None:
    try:
        data, fs = sf.read(str(path), dtype="float32")
        sd.play(data, fs)
        sd.wait()
    except (sf.LibsndfileError, OSError, RuntimeError) as err:
        print(f"Failed to play audio: {err}")


def concat(input_files: Sequence[str], output: Path) -> None:
    """Concatenate .wav files into one using ffmpeg."""
    list_path = OUTDIR / "temp_list.txt"
    with list_path.open("w", encoding="utf-8") as f:
        f.writelines(f"file '{file}'\n" for file in input_files)

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


def make_quarters() -> None:
    for n in range(1, 4):
        pops = [POP] * n
        output = OUTDIR / f"quarter_{n}.wav"
        concat(pops, output)


def make_hours() -> None:
    for hour in range(1, 13):
        clusters: list[str] = []
        remaining = hour
        while remaining >= POPS_PER_CLUSTER:
            clusters.extend([POP] * POPS_PER_CLUSTER)
            clusters.append(SILENCE)
            remaining -= POPS_PER_CLUSTER
        if remaining > 0:
            clusters.extend([POP] * remaining)
        output = OUTDIR / f"hour_{hour}.wav"
        concat([CHIME, *clusters], output)


def make_silence() -> None:
    subprocess.run(  # noqa: S603
        [
            FFMPEG,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-t",
            "0.2",
            str(SILENCE),
        ],
        check=True,
    )


def build_all() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    make_silence()
    make_quarters()
    make_hours()
