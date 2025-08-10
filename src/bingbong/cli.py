from __future__ import annotations

import subprocess  # noqa: S404
import sys
import time
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

import click

from bingbong.audio import play_once, play_repeated
from bingbong.config import APP_NAME, LABEL, Config, ConfigNotFoundError, config_path
from bingbong.constants import CHIME_DELAY, POP_DELAY
from bingbong.core import compute_pop_count, get_silence_until, set_silence_for, silence_active
from bingbong.service import service

if TYPE_CHECKING:
    from onginred.service import LaunchdService


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:
    """Bingbong - gentle time chimes for macOS."""


def _default_wavs() -> tuple[str, str]:
    """Locate packaged default wav files.

    Returns `(chime_path, pop_path)` as filesystem paths (str).
    """
    # Ensure the resources live inside the package at runtime (wheel or editable).
    pkg = "bingbong.data"
    chime = resources.files(pkg) / "chime.wav"
    pop = resources.files(pkg) / "pop.wav"
    return (str(chime), str(pop))


def _get_service(plist_path: str | None) -> LaunchdService:
    python = sys.executable
    args = [python, "-m", APP_NAME, "tick"]
    return service(plist_path, args)


@cli.command()
@click.option(
    "--chime",
    "chime_wav",
    required=False,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the chime .wav (defaults to packaged sound)",
)
@click.option(
    "--pop",
    "pop_wav",
    required=False,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the pop .wav (defaults to packaged sound)",
)
@click.option(
    "--plist-path", type=click.Path(dir_okay=False), default=None, help="Optional explicit plist path"
)
def install(chime_wav: str, pop_wav: str, plist_path: str | None) -> None:
    """Install and load the background chime service."""
    # Fall back to packaged defaults if not provided.
    if not chime_wav or not pop_wav:
        def_chime, def_pop = _default_wavs()
        chime_wav = chime_wav or def_chime
        pop_wav = pop_wav or def_pop

    # Persist config for the tick runner
    Config(chime_wav=chime_wav, pop_wav=pop_wav).save()

    # Program arguments: invoke this module with 'tick'
    svc = _get_service(plist_path)

    try:
        svc.install()
        click.secho(f"[bingbong] Installed {LABEL}", fg="green")
        click.echo(f"  plist: {svc.plist_path}")
        click.echo(f"  chime: {chime_wav}")
        click.echo(f"   pop : {pop_wav}")

    except (OSError, subprocess.CalledProcessError) as e:
        click.secho(f"[bingbong] Install failed: {e}", fg="red")
        sys.exit(1)


@cli.command()
@click.option(
    "--plist-path",
    type=click.Path(dir_okay=False),
    default=None,
    help="Explicit plist path if you used one at install",
)
def uninstall(plist_path: str | None) -> None:
    """Unload and remove the background chime service."""
    svc = _get_service(plist_path)

    try:
        svc.uninstall()
        click.secho(f"[bingbong] Uninstalled {LABEL}", fg="yellow")

    except (OSError, subprocess.CalledProcessError) as e:
        click.secho(f"[bingbong] Uninstall failed: {e}", fg="red")
        sys.exit(1)


@cli.command()
def status() -> None:
    """Show config, silence state, and where the plist would live."""
    click.echo(f"Label: {LABEL}")
    default_plist = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    click.echo(f"Default plist path: {default_plist}")

    if config_path().exists():
        try:
            cfg = Config.load()
        except ConfigNotFoundError as e:
            click.echo(f"[bingbong] {e} Run: bingbong install ...", err=True)
            sys.exit(1)
        click.echo(f"Chime: {cfg.chime_wav}")
        click.echo(f"Pop  : {cfg.pop_wav}")
    else:
        click.echo("Config: (not found)")

    if default_plist.exists():
        click.secho("Plist present ✅", fg="green")
    else:
        click.secho("Plist not present ❌", fg="yellow")

    until = get_silence_until()
    if until and datetime.now(UTC) < until:
        mins = int((until - datetime.now(UTC)).total_seconds() // 60)
        click.secho(
            f"Silenced for another ~{mins} min (until {until.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')})",
            fg="blue",
        )
    else:
        click.echo("Silence: off")


@cli.command()
@click.option("--minutes", type=int, required=True, help="Minutes to pause bingbong")
def silence(minutes: int) -> None:
    """Temporarily silence all chimes."""
    if minutes <= 0:
        click.echo("Minutes must be > 0")
        sys.exit(2)
    until = set_silence_for(minutes)
    click.secho(f"[bingbong] Silenced until {until.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}", fg="blue")


@cli.command()
def tick() -> None:
    """Decides what to play & respects silence windows.

    Called by launchd at :00/:15/:30/:45.
    """
    # If silenced, exit quietly
    if silence_active():
        return

    cfg = Config.load()
    # explicit local wall clock for clarity (not UTC):
    now_local = datetime.now().astimezone()
    pop_count, do_chime = compute_pop_count(now_local.minute, now_local.hour)

    if pop_count == 0:
        return

    if do_chime:
        play_once(cfg.chime_wav)
        time.sleep(CHIME_DELAY)

    play_repeated(cfg.pop_wav, pop_count, delay=POP_DELAY)


def main() -> None:
    """Compatibility entry point for `pyproject.toml` (`bingbong.cli:main`)."""
    # "call the Click group" pattern
    cli()
