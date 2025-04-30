"""Notify the user with the appropriate chime based on time."""

from datetime import datetime
from pathlib import Path

from .audio import build_all, play_file
from .paths import OUTDIR


def nearest_quarter(minute: int) -> int:
    """Convert minute to nearest quarter (0-3)."""
    return round(minute / 15) % 4


def resolve_chime_path(hour: int, nearest: int) -> Path:
    if nearest == 0:
        hour = (hour % 12) + 1
        return OUTDIR / f"hour_{hour}.wav"
    return OUTDIR / f"quarter_{nearest}.wav"


def notify_time() -> None:
    now = datetime.now().astimezone()
    hour = now.hour % 12 or 12
    minute = now.minute

    nearest = nearest_quarter(minute)
    chime_path = resolve_chime_path(hour, nearest)

    if not chime_path.exists():
        print(f"Warning: {chime_path} does not exist.")
        print("Attempting to rebuild chime files...")

        try:
            build_all()
            print("Rebuild complete.")
        except RuntimeError as err:  # ✅ Specific error
            print(f"Error during rebuild: {err}")
            return

        if not chime_path.exists():
            print("Rebuild failed or file still missing. Aborting chime.")
            return

    play_file(chime_path)
