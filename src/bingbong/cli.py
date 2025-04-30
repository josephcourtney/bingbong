import shutil

import click

from . import audio, launchctl, notify
from .paths import OUTDIR


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
    if OUTDIR.exists():
        shutil.rmtree(OUTDIR)
        click.echo(f"Removed: {OUTDIR}")
    else:
        click.echo("No generated files found.")


@main.command()
def chime():
    """Play the appropriate chime for the current time."""
    notify.notify_time()
    click.echo("Chime played.")
