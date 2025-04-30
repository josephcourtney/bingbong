from datetime import datetime

from .audio import play_file, build_all
from .paths import OUTDIR


def nearest_quarter(minute: int) -> int:
    return round(minute / 15) % 4


def notify_time():
    now = datetime.now()
    hour = now.hour % 12 or 12  # 12-hour format
    minute = now.minute

    nearest = nearest_quarter(minute)

    if nearest == 0:
        # We're rounding to the top of the *next* hour
        hour = (hour % 12) + 1
        chime_path = OUTDIR / f"hour_{hour}.wav"
    else:
        chime_path = OUTDIR / f"quarter_{nearest}.wav"

    if not chime_path.exists():
        print(f"Warning: {chime_path} does not exist.")
        print("Attempting to rebuild chime files...")
        try:
            audio.build_all()
            print("Rebuild complete.")
        except Exception as e:
            print(f"Error during rebuild: {e}")
            return

        if not chime_path.exists():
            print("Rebuild failed or file still missing. Aborting chime.")
            return

    play_file(chime_path)
