import shutil
import subprocess  # noqa: S404
from pathlib import Path

import click

from . import audio, launchctl, notify
from .audio import FFMPEG
from .paths import ensure_outdir

PLIST_LABEL = "com.josephcourtney.bingbong"
STDOUT_LOG = Path("/tmp/bingbong.out")  # noqa: S108
STDERR_LOG = Path("/tmp/bingbong.err")  # noqa: S108


@click.group()
def main():
    """Time-based macOS notifier."""


@main.command()
def build():
    """Build composite chime/quarter audio files."""
    try:
        if not FFMPEG:
            click.echo("Error: ffmpeg is not available on this system.")
            return
        audio.build_all()
        click.echo("Built chime and quarter audio files.")
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


@main.command()
def logs():
    """Display the latest logs for the launchctl job."""
    for log in [STDOUT_LOG, STDERR_LOG]:
        click.echo(f"\n--- {log} ---")
        if log.exists():
            click.echo(log.read_text())
        else:
            click.echo("No log found.")
