import logging
import shutil
import subprocess  # noqa: S404
import sys
import tomllib
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import available_timezones

import click
import tomlkit
from croniter import croniter
from tomlkit import parse

from . import audio, launchctl, notify
from .ffmpeg import ffmpeg_available
from .notify import is_paused, on_wake
from .paths import ensure_outdir

# --- Logging & rotation setup ---
LOG_DIR = Path.home() / "Library" / "Logs"
LOG_FILE = LOG_DIR / "bingbong.log"
STDOUT_LOG = Path("/tmp/bingbong.out")  # noqa: S108
STDERR_LOG = Path("/tmp/bingbong.err")  # noqa: S108
LOG_ROTATE_SIZE = 10_000_000  # bytes


# Work around tests that call tomllib.loads on raw bytes:
def _loads(s, **kw):
    if isinstance(s, (bytes, bytearray)):
        s = s.decode("utf-8")
    return tomllib.loads(s, **kw)


def _rotate_logs():
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > LOG_ROTATE_SIZE:
            rotated = LOG_FILE.with_suffix(".log.1")
            if rotated.exists():
                rotated.unlink()
            LOG_FILE.rename(rotated)
    except OSError:
        # Defer to doctor to report; here just skip
        pass


_rotate_logs()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger("bingbong.cli")


# --- Paths & config ---
def config_path() -> Path:
    """Location of the user's ~/.config/bingbong/config.toml equivalent under XDG_DATA_HOME."""
    return ensure_outdir() / "config.toml"


def read_config():
    path = config_path()
    return _loads(path.read_bytes())


@click.group()
def main():
    """Time-based macOS notifier."""


def _parse_time_range(rng):
    start, end = rng.split("-")
    sh, sm = map(int, start.split(":"))
    eh, em = map(int, end.split(":"))
    if (eh, em) == (sh, sm):
        msg = "Start and end times are the same"
        raise ValueError(msg)
    return rng


@main.command()
def configure():
    """Run interactive configuration wizard."""
    ensure_outdir()
    cfg = tomlkit.document()

    # 1) chime_schedule
    cron = click.prompt("Chime schedule (cron)", default="0 * * * *")
    if not croniter.is_valid(cron):

        def abort():
            click.echo("Invalid cron; aborting.", err=True)
            sys.exit(1)

        abort()

    cfg["chime_schedule"] = cron

    # 2) suppress_schedule
    suppress = []
    if click.confirm("Add suppression windows (quiet hours)?", default=False):
        while True:
            rng = click.prompt("Enter time range HH:MM-HH:MM")
            try:
                suppress.append(_parse_time_range(rng))
            except ValueError:
                click.echo("Invalid time range; aborting.", err=True)
                sys.exit(1)
            if not click.confirm("Add another suppression window?", default=False):
                break

    cfg["suppress_schedule"] = suppress

    # 3) respect DND
    cfg["respect_dnd"] = click.confirm("Respect macOS Do Not Disturb?", default=True)

    # 4) timezone override
    tz = click.prompt("Timezone (IANA name) or blank for system", default="")
    if tz:
        if tz not in available_timezones():
            click.echo("Invalid timezone; aborting.")
            sys.exit(1)
        cfg["timezone"] = tz

    # 5) custom sounds
    custom = click.prompt("Custom sounds (comma-separated paths) or blank", default="")
    if custom:
        paths = [p.strip() for p in custom.split(",") if p.strip()]
        cfg["custom_sounds"] = paths

    # Write out
    config_path().write_text(tomlkit.dumps(cfg), encoding="utf-8")
    click.echo(f"Wrote configuration to {config_path()}")


@main.command()
def build():
    """Build composite chime/quarter audio files."""
    if not ffmpeg_available():
        click.echo("ffmpeg is not available")
        return
    try:
        audio.build_all()
        logger.info("Built chime and quarter audio files.")
    except RuntimeError as err:
        click.echo(str(err))


@main.command()
def install():
    """Install launchctl job with cron-driven schedule."""
    # Load config if present
    # we let launchctl.install pick up its own default or stored config

    if config_path().exists():
        # merge in any user config first
        parse(config_path().read_text(encoding="utf-8"))
        # but we don't pass it here (launchctl reads separately)
        # so we can validate early
        # ...optionally validate cfg["chime_schedule"] here...
    try:
        launchctl.install()
    except ValueError as e:
        click.echo(f"Invalid cron: {e}")
        sys.exit(1)


@main.command()
def uninstall():
    """Remove launchctl job."""
    launchctl.uninstall()
    click.echo("Uninstalled launchctl job.")


@main.command()
def clean():
    """Delete generated audio files."""
    outdir = ensure_outdir()
    if outdir.exists():
        shutil.rmtree(outdir)
        click.echo(f"Removed: {outdir}")
    else:
        click.echo("No generated files found.")


@main.command()
def chime():
    """Play the appropriate chime for the current time."""
    notify.notify_time()
    click.echo("Chime played.")


@main.command()
def status():
    """Check service status and next events."""
    # 1) service loaded?
    launchctl_path = shutil.which("launchctl")
    result = subprocess.run([launchctl_path, "list"], capture_output=True, text=True, check=False)  # noqa: S603
    loaded = (
        "✅ Service is loaded." if launchctl.PLIST_LABEL in result.stdout else "❌ Service is NOT loaded."
    )
    click.echo(loaded)

    now = datetime.now().astimezone()
    # 2) manual pause
    pause_until = is_paused(ensure_outdir(), now)
    if pause_until:
        click.echo(f"🔕 Chimes paused until {pause_until:%H:%M}")
        return

    # 3) scheduled suppression
    try:
        cfg = read_config()
    except FileNotFoundError:
        click.echo("Error: configuration file not found; please run `bingbong configure`", err=True)
        sys.exit(1)

    for rng in cfg.get("suppress_schedule", []):
        start, end = rng.split("-")
        st = now.replace(hour=int(start[:2]), minute=int(start[3:]), second=0, microsecond=0)
        en = now.replace(hour=int(end[:2]), minute=int(end[3:]), second=0, microsecond=0)
        if st <= now < en:
            click.echo(f"Suppressed until {en:%H:%M}")
            return

    # 4) next chime
    cron = cfg["chime_schedule"]
    nxt = croniter(cron, now).get_next(datetime)
    click.echo(f"Next chime: {nxt:%H:%M}")


@main.command()
@click.option("--minutes", type=int, help="Pause for N minutes.")
@click.option("--until-tomorrow", is_flag=True, help="Pause until 8 AM tomorrow.")
def pause(minutes, until_tomorrow):
    """Temporarily silence all chimes."""
    now = datetime.now().astimezone()
    if minutes is not None and until_tomorrow:
        msg = "Cannot combine --minutes with --until-tomorrow"
        raise click.UsageError(msg)
    if until_tomorrow:
        tomorrow = (now + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
        expiry = tomorrow
    elif minutes is not None:
        expiry = now + timedelta(minutes=minutes)
    else:
        msg = "Specify --minutes or --until-tomorrow"
        raise click.UsageError(msg)
    outdir = ensure_outdir()
    pause_file = outdir / ".pause_until"
    pause_file.write_text(expiry.isoformat())
    click.echo(f"🔕 Chimes paused until {expiry:%Y-%m-%d %H:%M}")


@main.command()
def unpause():
    """Resume chimes immediately (cancel any pending pause)."""
    outdir = ensure_outdir()
    pause_file = outdir / ".pause_until"
    if pause_file.exists():
        pause_file.unlink()
        click.echo("🔔 Chimes resumed.")
    else:
        click.echo("🔔 Chimes were not paused.")


@main.command()
def doctor():
    """Run diagnostics to verify setup and health."""
    click.echo("Running diagnostics on bingbong.")
    # launchctl
    launchctl_path = shutil.which("launchctl")
    if not launchctl_path:
        click.echo("Error: 'launchctl' not found in PATH.")
        sys.exit(1)
    result = subprocess.run([launchctl_path, "list"], capture_output=True, text=True, check=False)  # noqa: S603
    plist_loaded = launchctl.PLIST_LABEL in result.stdout
    click.echo(
        f"[{'x' if plist_loaded else ' '}] launchctl job is {'loaded' if plist_loaded else 'NOT loaded'}."
    )
    if not plist_loaded:
        click.echo("    try running `bingbong install` to load it.")

    # audio files
    outdir = ensure_outdir()
    required = {
        *(f"hour_{h}.wav" for h in range(1, 13)),
        *(f"quarter_{q}.wav" for q in (1, 2, 3)),
        "silence.wav",
    }
    existing = {p.name for p in outdir.iterdir()} if outdir.exists() else set()
    missing = sorted(required - existing)
    if not missing:
        click.echo(f"[x] All required audio files are present in {outdir}")
    else:
        click.echo(f"[ ] Missing audio files in {outdir}:")
        for f in missing:
            click.echo(f"   - {f}")
        click.echo("    if FFmpeg is installed, run `bingbong build` to create them.")

    # ffmpeg
    if ffmpeg_available():
        print("[x] FFmpeg is available")
    else:
        # more user-friendly phrasing for the doctor check
        print("[ ] FFmpeg cannot be found")

    # logs
    try:
        files = sorted((LOG_DIR).glob("bingbong.log*"))
        for p in files:
            click.echo(p.name)
    except OSError:
        click.echo("Cannot write logs; check permissions.")

    # summary exit
    if plist_loaded and not missing and ffmpeg_available():
        click.echo("Hooray! All systems go.")
        sys.exit(0)
    click.echo("Woe! One or more checks failed.")
    sys.exit(1)


@main.command()
def on_wake_cmd():
    """Handle wake event: play missed chimes."""
    on_wake(ensure_outdir())


@main.command()
@click.option("--clear", is_flag=True, help="Clear log files before showing.")
def logs(clear):
    """Show—or clear—service logs."""
    if clear:
        removed = False
        for p in (STDOUT_LOG, STDERR_LOG):
            if p.exists():
                try:
                    p.unlink()
                    removed = True
                except OSError:
                    click.echo(f"Error clearing {p}")
        click.echo((removed and "Cleared logs.") or "No logs to clear.")
        return

    any_found = False
    for p, label in [(STDOUT_LOG, "stdout"), (STDERR_LOG, "stderr")]:
        if p.exists():
            any_found = True
            click.echo(f"--- {label} log ({p}) ---")
            click.echo(p.read_text())
        else:
            click.echo(f"No {label} log found at {p}")
    if not any_found:
        click.echo("No log files found.")
