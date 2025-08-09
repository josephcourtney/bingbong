import logging
import shutil
import subprocess  # noqa: S404
from datetime import datetime, timedelta
from pathlib import Path

from . import audio, state
from .audio import build_all
from .console import ok
from .paths import ensure_outdir

logger = logging.getLogger("bingbong.notify")

HOURS_ON_CLOCK = 12


def nearest_quarter(minute: int) -> int:
    """Convert minute to nearest quarter (0-3)."""
    return round(minute / 15) % 4


def resolve_chime_path(hour: int, nearest: int, outdir: Path | None = None) -> Path:
    """Return the path to the correct chime file."""
    if outdir is None:
        outdir = ensure_outdir()
    if nearest == 0:
        # on the hour → play next hour's chime cluster
        next_hour = (hour % HOURS_ON_CLOCK) + 1
        return outdir / f"hour_{next_hour}.wav"
    return outdir / f"quarter_{nearest}.wav"


def is_paused(outdir: Path, now: datetime) -> datetime | None:
    """Return the pause expiry if active; clear entry if expired/invalid."""
    data = state.load(outdir)
    raw = data.get("pause_until")
    if not raw:
        return None

    try:
        expiry_raw = datetime.fromisoformat(raw)
    except ValueError:
        logger.warning("Corrupt pause file; deleting.")
        _ = data.pop("pause_until", None)
        state.save(outdir, data)
        return None

    if expiry_raw.tzinfo is None:
        expiry_raw = expiry_raw.replace(tzinfo=now.tzinfo)

    if now >= expiry_raw:
        _ = data.pop("pause_until", None)
        state.save(outdir, data)
        return None
    return expiry_raw


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
    except RuntimeError:
        logger.exception("Error during rebuild")
        return False

    if not chime_path.exists():
        logger.error("Rebuild failed or file still missing: %s", chime_path)
        return False

    logger.info("Rebuild complete.")
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

    logger.debug("now=%s", now)
    logger.debug("hour=%s", hour)
    logger.debug("nearest=%s", nearest)
    logger.debug("chime_path=%s", chime_path)

    # 4) Rebuild if missing
    if not chime_path.exists() and not _ensure_chime_exists(chime_path):
        return

    # 5) Duck other audio if possible
    try:
        audio.duck_others()
    except OSError as e:
        logger.warning("warning: %s", e)

    # 6) Play the chime
    ok(f"{now.isoformat()} {chime_path.name}")
    audio.play_file(chime_path)


def on_wake(outdir: Path | None = None) -> None:
    """Play missed hourly chimes since the last recorded run."""
    if outdir is None:
        outdir = ensure_outdir()

    data = state.load(outdir)
    now = datetime.now().astimezone()

    last_raw = data.get("last_run")
    if not last_raw:
        data["last_run"] = now.isoformat()
        state.save(outdir, data)
        return

    try:
        last = datetime.fromisoformat(last_raw)
    except ValueError:
        last = now
    if last.tzinfo is None:
        last = last.replace(tzinfo=now.tzinfo)

    current = last.replace(minute=0, second=0, microsecond=0)

    while current + timedelta(hours=1) < now:
        current += timedelta(hours=1)
        path = resolve_chime_path(current.hour, 0, outdir)
        if path.exists():
            ok(f"{current.isoformat()} {path.name}")
            audio.play_file(path)

    data["last_run"] = now.isoformat()
    state.save(outdir, data)
