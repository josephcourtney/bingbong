import logging
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
POPS_PER_CLUSTER = 3


def play_file(path: Path) -> None:
    try:
        data, fs = sf.read(str(path), dtype="float32")
        sd.play(data, fs)
        sd.wait()
    except (sf.LibsndfileError, OSError, RuntimeError) as err:
        logger = logging.getLogger("bingbong.audio")
        logger.exception("Failed to play audio: %s", path)
        # so that our pytest capsys picks it up:
        print(f"Failed to play audio: {err}")


def make_quarters(outdir: Path | None = None) -> None:
    if outdir is None:
        outdir = ensure_outdir()
    for n in range(1, 4):
        pops = [POP] * n
        output = outdir / f"quarter_{n}.wav"
        concat([str(outdir / "silence.wave"), *pops], output, outdir=outdir)


def make_hours(outdir: Path | None = None) -> None:
    if outdir is None:
        outdir = ensure_outdir()
    for hour in range(1, 13):
        clusters = [POP] * (hour - 1)
        output = outdir / f"hour_{hour}.wav"
        concat([CHIME, *clusters], output, outdir=outdir)
        concat([str(outdir / "silence.wave"), CHIME, *clusters], output, outdir=outdir)


def build_all(outdir: Path | None = None) -> None:
    make_silence(outdir)
    make_quarters(outdir)
    make_hours(outdir)
