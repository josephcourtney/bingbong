import shutil

import click

from . import audio, launchctl, notify
from .paths import DEFAULT_OUTDIR

import subprocess
from pathlib import Path

PLIST_LABEL = "com.josephcourtney.bingbong"
STDOUT_LOG = Path("/tmp/bingbong.out")
STDERR_LOG = Path("/tmp/bingbong.err")


@click.group()
def main():
    """Time-based macOS notifier."""


@main.command()
def build():
    """Build composite chime/quarter audio files."""
    audio.build_all()
    click.echo("Built chime and quarter audio files.")


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
    if DEFAULT_OUTDIR.exists():
        shutil.rmtree(DEFAULT_OUTDIR)
        click.echo(f"Removed: {DEFAULT_OUTDIR}")
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
    result = subprocess.run(
        ["/bin/launchctl", "list"],
        capture_output=True,
        text=True,
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
