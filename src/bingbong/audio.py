import logging
import math
from importlib.resources import files
from pathlib import Path

import sounddevice as sd
import soundfile as sf

from .ffmpeg import concat, make_silence
from .paths import ensure_outdir

# --- Constants ---
DATA = files("bingbong.data")
POP = str(DATA / "pop.wav")
CHIME = str(DATA / "chime.wav")
SILENCE = str(DATA / "silence.wav")
POPS_PER_CLUSTER = 3


def play_file(path: Path) -> None:
    logging.getLogger("bingbong.audio")
    if not path.exists():
        print("Failed to play audio: file not found")
        return

    try:
        data, fs = sf.read(str(path))
    except (RuntimeError, OSError) as err:
        print(f"Failed to play audio: {err}")
        return

    try:
        sd.play(data, fs)
        sd.wait()
    except (RuntimeError, OSError) as err:
        print(f"Failed to play audio: {err}")
        return


def duck_others() -> None:
    """Lower the volume of other applications while we chime.

    No-op stub; override in real implementations.
    """
    return


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
        cluster = []
        for _ in range(math.ceil(hour / POPS_PER_CLUSTER)):
            if remaining_ > POPS_PER_CLUSTER:
                cluster.extend([POP] * POPS_PER_CLUSTER + [SILENCE])
                remaining_ -= POPS_PER_CLUSTER
            else:
                cluster.extend([POP] * remaining_ + [SILENCE])

        output = outdir / f"hour_{hour}.wav"
        concat([SILENCE, CHIME, SILENCE, *cluster], output, outdir=outdir)


def build_all(outdir: Path | None = None) -> None:
    make_silence(outdir)
    make_quarters(outdir)
    make_hours(outdir)
