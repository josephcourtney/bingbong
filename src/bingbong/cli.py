import logging
import shutil
import subprocess  # noqa: S404
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import click

from . import audio, launchctl, notify
from .ffmpeg import ffmpeg_available
from .notify import is_paused
from .paths import ensure_outdir

with tempfile.NamedTemporaryFile(prefix="bingbong-out-", delete=False) as out_fh:
    STDOUT_LOG = Path(out_fh.name)
with tempfile.NamedTemporaryFile(prefix="bingbong-err-", delete=False) as err_fh:
    STDERR_LOG = Path(err_fh.name)

PLIST_LABEL = "com.josephcourtney.bingbong"

# configure root logger once
logger = logging.getLogger("bingbong")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
logger.addHandler(handler)


@click.group()
def main():
    """Time-based macOS notifier."""


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
    """Install launchctl job."""
    launchctl.install()
    click.echo("Installed launchctl job.")


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
    """Check whether the launchctl job is currently loaded."""
    launchctl_path = shutil.which("launchctl")
    result = subprocess.run(  # noqa: S603
        [launchctl_path, "list"],
        capture_output=True,
        text=True,
        check=False,
    )
    if PLIST_LABEL in result.stdout:
        click.echo("✅ Service is loaded.")
    else:
        click.echo("❌ Service is NOT loaded.")
    now = datetime.now().astimezone()
    pause_until = is_paused(ensure_outdir(), now)
    if pause_until:
        click.echo(f"🔕 Chimes paused until {pause_until:%Y-%m-%d %H:%M}")


@main.command()
@click.option("--clear", is_flag=True, help="Clear log files instead of displaying them.")
def logs(*, clear: bool) -> None:
    """Display or clear the latest logs for the launchctl job."""
    for log in [STDOUT_LOG, STDERR_LOG]:
        click.echo(f"\n--- {log} ---")
        if log.exists():
            if clear:
                log.unlink()
                click.echo("Cleared.")
            else:
                click.echo(log.read_text())
        else:
            click.echo("No log found.")


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
        # assume wake at 8 AM local time
        tomorrow = (now + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
        expiry = tomorrow
    elif minutes:
        expiry = now + timedelta(minutes=minutes)
    else:
        msg = "Specify --minutes or --until-tomorrow"
        raise click.UsageError(msg)

    # write expiry to file
    outdir = ensure_outdir()
    pause_file = outdir / ".pause_until"
    pause_file.write_text(expiry.isoformat())
    click.echo(f"🔕 Chimes paused until {expiry:%Y-%m-%d %H:%M}")


@main.command()
def doctor():
    """Run diagnostics to verify setup and health."""
    click.echo("Running diagnostics on bingbong.")

    launchctl_path = shutil.which("launchctl")
    if not launchctl_path:
        click.echo("Error: 'launchctl' not found in PATH.")
        raise SystemExit(1)

    # Check if launchctl job is loaded
    result = subprocess.run(  # noqa: S603
        [launchctl_path, "list"],
        capture_output=True,
        text=True,
        check=False,
    )
    plist_loaded = PLIST_LABEL in result.stdout
    if plist_loaded:
        click.echo("[x] launchctl job is loaded.")
    else:
        click.echo("[ ] launchctl job is NOT loaded.")
        click.echo("    try running `bingbong install` to load it.")

    # Check audio files
    outdir = ensure_outdir()
    required_files = {
        "hour_1.wav",
        "hour_2.wav",
        "hour_3.wav",
        "hour_4.wav",
        "hour_5.wav",
        "hour_6.wav",
        "hour_7.wav",
        "hour_8.wav",
        "hour_9.wav",
        "hour_10.wav",
        "hour_11.wav",
        "hour_12.wav",
        "quarter_1.wav",
        "quarter_2.wav",
        "quarter_3.wav",
        "silence.wav",
    }
    existing_files = {p.name for p in outdir.iterdir()} if outdir.exists() else set()
    missing_files = sorted(required_files - existing_files)

    if not missing_files:
        click.echo(f"[x] All required audio files are present in {outdir}")
    else:
        click.echo(f"[ ] Missing audio files in {outdir}:")
        for f in missing_files:
            click.echo(f"   - {f}")
        click.echo("    if FFmpeg is installed, run `bingbong build` to create them.")

    if ffmpeg_available():
        click.echo("[x] FFmpeg is available")
    else:
        click.echo("[ ] FFmpeg cannot be found. Is it installed?")

    click.echo("")
    # Exit code summary
    if plist_loaded and not missing_files and ffmpeg_available():
        click.echo("Hooray! All systems go.")
        raise SystemExit(0)
    click.echo("Woe! One or more checks failed.")
    raise SystemExit(1)


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
