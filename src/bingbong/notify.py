import contextlib
import logging
import shutil
import subprocess  # noqa: S404
from datetime import UTC, datetime, timedelta
from pathlib import Path

from . import audio
from .audio import build_all
from .paths import ensure_outdir

logger = logging.getLogger("bingbong.notify")


def nearest_quarter(minute: int) -> int:
    return round(minute / 15) % 4


def resolve_chime_path(hour: int, nearest: int, outdir: Path | None = None) -> Path:
    if outdir is None:
        outdir = ensure_outdir()
    if nearest == 0:
        hour = (hour % 12) + 1
        return outdir / f"hour_{hour}.wav"
    return outdir / f"quarter_{nearest}.wav"


def is_paused(outdir: Path, now: datetime) -> datetime | None:
    pause_file = outdir / ".pause_until"
    if not pause_file.exists():
        return None
    try:
        expiry = datetime.fromisoformat(pause_file.read_text())
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        if now < expiry:
            return expiry
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
    if outdir is None:
        outdir = ensure_outdir()
    now = datetime.now().astimezone()
    # manual pause
    if is_paused(outdir, now):
        return
    # DND
    defaults = shutil.which("defaults")
    if defaults:
        try:
            res = subprocess.run(  # noqa: S603
                [defaults, "-currentHost", "read", "com.apple.notificationcenterui", "doNotDisturb"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.stdout.strip() == "1":
                return
        except (ValueError, OSError):
            logger.warning("DND check failed")
    # determine path
    hour = now.hour % 12 or 12
    nearest = nearest_quarter(now.minute)
    path = resolve_chime_path(hour, nearest, outdir)
    # rebuild if missing
    if not path.exists():
        logger.warning("%s missing; attempting rebuild...", path)
        try:
            build_all()
        except RuntimeError as err:
            print(f"Error during rebuild: {err}")
            return
        if not path.exists():
            logger.error("Rebuild failed or file still missing: %s", path)
            print("Rebuild failed or file still missing.")
            return
        print("Rebuild complete.")
    # duck and play
    with contextlib.suppress(Exception):
        audio.duck_others()
    audio.play_file(path)


def _next_quarter(dt: datetime) -> datetime:
    # Round down to the last quarter, then bump if we're past it
    base = dt.replace(
        minute=(dt.minute // 15) * 15,
        second=0,
        microsecond=0,
    )
    if base <= dt:
        base += timedelta(minutes=15)
    return base


def on_wake(outdir: Path | None = None) -> None:
    if outdir is None:
        outdir = ensure_outdir()
    outdir.mkdir(parents=True, exist_ok=True)

    now = datetime.now().astimezone()
    state = outdir / ".last_run"

    # First run: record and exit
    if not state.exists():
        state.write_text(now.isoformat())
        return

    # Read last run time
    last = datetime.fromisoformat(state.read_text())

    # Iterate true quarter marks > last, ≤ now
    cursor = _next_quarter(last)
    while cursor <= now:
        # Determine which chime to play
        hour = cursor.hour % 12 or 12
        q = nearest_quarter(cursor.minute)
        path = resolve_chime_path(hour, q, outdir)

        # If missing, try rebuilding once
        if not path.exists():
            try:
                build_all(outdir)
            except RuntimeError:
                # rebuild failed—skip this slot
                cursor += timedelta(minutes=15)
                continue
            if not path.exists():
                cursor += timedelta(minutes=15)
                continue

        # Play it (ducking other audio is optional)
        with contextlib.suppress(Exception):
            audio.duck_others()
        audio.play_file(path)

        cursor += timedelta(minutes=15)

    # Update state for next wake
    state.write_text(now.isoformat())
