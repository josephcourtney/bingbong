import logging
from importlib.resources import files
from pathlib import Path

import sounddevice as sd
import soundfile as sf

from .ffmpeg import concat, make_silence
from .paths import ensure_outdir
import logging
import subprocess
from pathlib import Path


# --- Constants ---
DATA = files("bingbong.data")
POP = str(DATA / "pop.wav")
CHIME = str(DATA / "chime.wav")
SILENCE = str(DATA / "silence.wav")
POPS_PER_CLUSTER = 3


def play_file(path: Path) -> None:
    logger = logging.getLogger("bingbong.audio")
    try:
        # fire-and-forget via afplay
        subprocess.run(["afplay", str(path)], check=True)
    except FileNotFoundError:
        # afplay isn’t on PATH
        logger.exception("`afplay` command not found; cannot play audio: %s", path)
        print("Failed to play audio: `afplay` not found")
    except subprocess.CalledProcessError as err:
        # playback failed
        logger.exception("Playback failed for %s: %s", path, err)
        print(f"Failed to play audio: {err}")


def make_quarters(outdir: Path | None = None) -> None:
    if outdir is None:
        outdir = ensure_outdir()
    for n in range(1, 4):
        pops = [POP] * n
        output = outdir / f"quarter_{n}.wav"
        concat([str(outdir / "silence.wav"), *pops], output, outdir=outdir)


def make_hours(outdir: Path | None = None) -> None:
    if outdir is None:
        outdir = ensure_outdir()
    for hour in range(1, 13):
        remaining_ = hour
        clusters = []
        for i in range(hour):
            if remaining_ > POPS_PER_CLUSTER:
                clusters.extend([POP] * POPS_PER_CLUSTER + [SILENCE])
                remaining_ -= POPS_PER_CLUSTER
            else:
                clusters.extend([POP] * remaining_ + [SILENCE])

        output = outdir / f"hour_{hour}.wav"
        concat([SILENCE, CHIME, SILENCE, *clusters], output, outdir=outdir)


def build_all(outdir: Path | None = None) -> None:
    make_silence(outdir)
    make_quarters(outdir)
    make_hours(outdir)
