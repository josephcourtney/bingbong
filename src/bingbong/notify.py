import logging
import shutil
import subprocess  # noqa: S404
from datetime import datetime
from pathlib import Path

from . import audio
from .audio import build_all
from .paths import ensure_outdir

logger = logging.getLogger("bingbong.notify")


def nearest_quarter(minute: int) -> int:
    """Convert minute to nearest quarter (0-3)."""
    return round(minute / 15) % 4


def resolve_chime_path(hour: int, nearest: int, outdir: Path | None = None) -> Path:
    """Return the path to the correct chime file."""
    if outdir is None:
        outdir = ensure_outdir()
    if nearest == 0:
        hour %= 12
        hour = hour if hour != 12 else 12
        return outdir / f"hour_{hour}.wav"

    return outdir / f"quarter_{nearest}.wav"


def is_paused(outdir: Path, now: datetime) -> datetime | None:
    """Check for a valid pause file; remove it if expired or invalid."""
    pause_file = outdir / ".pause_until"
    if not pause_file.exists():
        return None
    try:
        expiry_raw = datetime.fromisoformat(pause_file.read_text())
        expiry_today = now.replace(
            hour=expiry_raw.hour,
            minute=expiry_raw.minute,
            second=expiry_raw.second,
            microsecond=0,
        )
        if now < expiry_today:
            return expiry_today
    except (ValueError, OSError) as e:
        logger.warning("Invalid pause file; removing it: %s", e)
    pause_file.unlink(missing_ok=True)
    return None


def _in_dnd() -> bool:
    """Return True if macOS Do Not Disturb is currently enabled."""
    defaults = shutil.which("defaults")
    if not defaults:
        logger.warning("`defaults` command not found; skipping DND check")
        return False

    try:
        result = subprocess.run(  # noqa: S603
            [defaults, "-currentHost", "read", "com.apple.notificationcenterui", "doNotDisturb"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip() == "1"
    except (subprocess.SubprocessError, OSError) as e:
        logger.warning("DND check failed: %s", e)
        return False


def _ensure_chime_exists(chime_path: Path) -> bool:
    """
    Attempt to rebuild audio assets if the requested chime is missing.

    Returns True if after rebuilding the file exists.
    """
    logger.warning("%s is missing; attempting rebuild...", chime_path)
    try:
        # rebuild into the default outdir; this signature matches zero-arg stubs
        build_all()
    except RuntimeError as err:
        print(f"Error during rebuild: {err}")
        return False

    if not chime_path.exists():
        logger.error("Rebuild failed or file still missing: %s", chime_path)
        print("Rebuild failed or file still missing.")
        return False

    print("Rebuild complete.")
    return True


def notify_time(outdir: Path | None = None) -> None:
    """Play the appropriate chime for the current time, respecting pauses and DND."""
    if outdir is None:
        outdir = ensure_outdir()

    now = datetime.now().astimezone()

    # 1) Manual pause
    if is_paused(outdir, now):
        return

    # 2) macOS Do Not Disturb
    if _in_dnd():
        return

    # 3) Determine which chime to play
    hour = now.hour % 12 or 12
    nearest = nearest_quarter(now.minute)
    chime_path = resolve_chime_path(hour, nearest, outdir)

    print(f"{now=}")
    print(f"{hour=}")
    print(f"{nearest=}")
    print(f"{chime_path=}")

    # 4) Rebuild if missing
    if not chime_path.exists() and not _ensure_chime_exists(chime_path):
        return

    # 5) Play the chime
    audio.play_file(chime_path)
