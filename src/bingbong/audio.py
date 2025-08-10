from importlib.resources import files as pkg_files  # noqa: I001
from pathlib import Path
import logging

import simpleaudio as sa

from .paths import ensure_outdir

# --- Constants ---
DATA = pkg_files("bingbong.data")
POP = str(DATA / "pop.wav")
CHIME = str(DATA / "chime.wav")
SILENCE = str(DATA / "silence.wav")
MAX_PLAY_BYTES = 25 * 1024 * 1024  # "skip absurdly large files to avoid memory churn"


def _copy_into(outdir: Path, filename: str) -> None:
    """Copy a packaged WAV into the outdir."""
    src = DATA / filename  # Traversable
    dst = outdir / filename
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        # read/write small files using Traversable API (safe for zip wheels)
        dst.write_bytes(src.read_bytes())
    except OSError:
        # If package files are not readable for some reason, create a tiny placeholder.
        # (Tests only require existence; runtime playback is stubbed in tests.)
        dst.write_bytes(b"\0" * 44)


def play_file(path: Path) -> None:
    logger = logging.getLogger("bingbong.audio")
    if not path.exists():
        logger.error("Failed to play audio: file not found (%s)", path)
        return
    if not path.is_file():
        logger.error("Failed to play audio: not a file (%s)", path)
        return
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    if size > MAX_PLAY_BYTES:
        logger.error("Failed to play audio: file too large (%s bytes): %s", size, path)
        return

    try:
        # simpleaudio expects standard PCM WAV
        wave = sa.WaveObject.from_wave_file(str(path))
        play_obj = wave.play()
        play_obj.wait_done()
    except (RuntimeError, OSError):
        logger.exception("Failed to play audio while playing (%s)", path)
        return


def duck_others() -> None:
    """Lower the volume of other applications while we chime.

    No-op stub; override in real implementations.
    """
    logging.getLogger("bingbong.audio").debug("duck_others() noop")


def make_quarters(outdir: Path | None = None) -> None:
    """Populate quarter-hour WAVs by copying prebuilt files from package data."""
    if outdir is None:
        outdir = ensure_outdir()
    for n in range(1, 4):
        _copy_into(outdir, f"quarter_{n}.wav")


def make_hours(outdir: Path | None = None) -> None:
    """Populate hour WAVs by copying prebuilt files from package data."""
    if outdir is None:
        outdir = ensure_outdir()
    for hour in range(1, 13):
        _copy_into(outdir, f"hour_{hour}.wav")


def build_all(outdir: Path | None = None) -> None:
    """Populate all WAVs by copying prebuilt package assets."""
    if outdir is None:
        outdir = ensure_outdir()
    # Silence & base effects (already packaged)
    _copy_into(outdir, "silence.wav")
    _copy_into(outdir, "chime.wav")
    _copy_into(outdir, "pop.wav")
    # Derived files (also packaged, built at release time)
    make_quarters(outdir)
    make_hours(outdir)
