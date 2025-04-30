"""Notify the user with the appropriate chime based on time."""

from datetime import datetime
from pathlib import Path

from . import audio
from .audio import build_all
from .paths import ensure_outdir


def nearest_quarter(minute: int) -> int:
    """Convert minute to nearest quarter (0-3)."""
    return round(minute / 15) % 4


def resolve_chime_path(hour: int, nearest: int, outdir: Path | None = None) -> Path:
    """Return the path to the correct chime file.

    If outdir is None, import and use the current DEFAULT_OUTDIR.
    """
    if outdir is None:
        outdir = ensure_outdir()

    if nearest == 0:
        # On the hour, advance to the next hour (with wraparound)
        hour = (hour % 12) + 1
        return outdir / f"hour_{hour}.wav"

    return outdir / f"quarter_{nearest}.wav"


def notify_time(outdir: Path | None = None) -> None:
    """Play the appropriate chime for the current time.

    If the needed file is missing, attempt to rebuild all chime files.
    """
    if outdir is None:
        outdir = ensure_outdir()

    now = datetime.now().astimezone()
    hour = now.hour % 12 or 12
    minute = now.minute

    nearest = nearest_quarter(minute)
    chime_path = resolve_chime_path(hour, nearest, outdir)

    if not chime_path.exists():
        print(f"Warning: {chime_path} does not exist.")
        print("Attempting to rebuild chime files...")

        try:
            # Call this module's build_all so tests can monkeypatch notify.build_all
            build_all()
            print("Rebuild complete.")
        except RuntimeError as err:
            print(f"Error during rebuild: {err}")
            return

        if not chime_path.exists():
            print("Rebuild failed or file still missing. Aborting chime.")
            return

    # Delegate to the audio module so tests can monkeypatch audio.play_file
    audio.play_file(chime_path)
