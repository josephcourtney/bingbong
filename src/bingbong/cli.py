from __future__ import annotations

import contextlib
import os
import subprocess  # noqa: S404
import sys
import time
from datetime import UTC, datetime, timedelta
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

import click

from bingbong.audio import AFPLAY, play_once, play_repeated
from bingbong.config import APP_NAME, LABEL, Config, ConfigNotFoundError, config_path, silence_path
from bingbong.constants import CHIME_DELAY, POP_DELAY
from bingbong.core import (
    compute_pop_count,
    get_silence_until,
    set_silence_for,
    silence_active,
)
from bingbong.service import service
from bingbong.log import debug, set_verbose

if TYPE_CHECKING:
    from onginred.service import LaunchdService


__all__ = [
    "cli",
    "doctor",
    "install",
    "resume",
    "silence",
    "status",
    "tick",
    "uninstall",
]


def _require_darwin() -> None:
    if sys.platform != "darwin":
        click.secho("[bingbong] macOS (Darwin) only", fg="red", err=True)
        sys.exit(1)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose debug output")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Bingbong - gentle time chimes for macOS."""
    # Initialize verbosity for this process.
    set_verbose(verbose)
    if verbose:
        debug("verbose logging enabled")
        debug(f"python={sys.executable}")
        debug(f"platform={sys.platform}")


def _default_wavs() -> tuple[Path, Path]:
    """Locate packaged default wav files."""
    pkg = "bingbong.data"
    chime = resources.files(pkg) / "chime.wav"
    pop = resources.files(pkg) / "pop.wav"
    debug(f"default wavs resolved: chime={chime} pop={pop}")
    return (Path(chime), Path(pop))


def _get_service(plist_path: Path | None) -> LaunchdService:
    python = sys.executable
    args = [python, "-m", APP_NAME, "tick"]
    return service(str(plist_path) if plist_path else None, args)


def _quiet_hours_active(now: datetime) -> bool:
    span = os.environ.get("BINGBONG_QUIET_HOURS")
    if not span:
        return False
    try:
        start_s, end_s = span.split("-")
        start = datetime.strptime(start_s, "%H:%M").time()  # noqa: DTZ007
        end = datetime.strptime(end_s, "%H:%M").time()  # noqa: DTZ007
    except ValueError:
        return False
    t = now.time()
    if start <= end:
        return start <= t < end
    return t >= start or t < end


@cli.command()
@click.option(
    "--chime",
    "chime_wav",
    required=False,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to the chime .wav (defaults to packaged sound)",
)
@click.option(
    "--pop",
    "pop_wav",
    required=False,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to the pop .wav (defaults to packaged sound)",
)
@click.option(
    "--plist-path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Optional explicit plist path",
)
def install(chime_wav: Path | None, pop_wav: Path | None, plist_path: Path | None) -> None:
    """Install and load the background chime service."""
    _require_darwin()
    if not AFPLAY.exists() or not os.access(AFPLAY, os.X_OK):
        click.secho(f"[bingbong] player not found/executable at {AFPLAY}", fg="red", err=True)
        sys.exit(1)
    if not chime_wav or not pop_wav:
        def_chime, def_pop = _default_wavs()
        chime_wav = chime_wav or def_chime
        pop_wav = pop_wav or def_pop
    debug(f"install: chime={chime_wav} pop={pop_wav} plist={plist_path} player={AFPLAY}")

    Config(chime_wav=chime_wav, pop_wav=pop_wav).save()
    svc = _get_service(plist_path)

    try:
        svc.install()
        click.secho(f"[bingbong] Installed {LABEL}", fg="green")
        click.echo(f"  plist: {svc.plist_path}")
        click.echo(f"  chime: {chime_wav}")
        click.echo(f"   pop : {pop_wav}")
        click.echo(f"  player: {AFPLAY}")
        click.echo(f"  troubleshoot: launchctl print gui/$UID/{LABEL}")
    except (OSError, subprocess.CalledProcessError) as e:
        click.secho(f"[bingbong] Install failed: {e}", fg="red")
        sys.exit(1)


@cli.command()
@click.option(
    "--plist-path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Explicit plist path if you used one at install",
)
def uninstall(plist_path: Path | None) -> None:
    """Unload and remove the background chime service."""
    _require_darwin()
    svc = _get_service(plist_path)

    try:
        svc.uninstall()
        click.secho(f"[bingbong] Uninstalled {LABEL}", fg="yellow")

    except (OSError, subprocess.CalledProcessError) as e:
        click.secho(f"[bingbong] Uninstall failed: {e}", fg="red")
        sys.exit(1)


@cli.command()
def status() -> None:
    """Show config, silence state, player, and plist status."""
    _require_darwin()
    debug("status: begin")
    click.echo(f"Label: {LABEL}")
    click.echo(f"Player: {AFPLAY}")
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
        click.secho(f"Plist not present ❌ (expected at {default_plist})", fg="yellow")

    until = get_silence_until()
    if until and datetime.now(UTC) < until:
        mins = int((until - datetime.now(UTC)).total_seconds() // 60)
        click.secho(
            f"Silenced for another ~{mins} min (until {until.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')})",
            fg="blue",
        )
    else:
        click.echo("Silence: off")
    debug("status: end")


@cli.command()
@click.option("--minutes", type=int, help="Minutes to pause bingbong")
@click.option("--until", type=str, help="Silence until HH:MM (24h)")
def silence(minutes: int | None, until: str | None) -> None:
    """Temporarily silence all chimes."""
    _require_darwin()
    if (minutes is None) == (until is None):
        click.echo("Provide either --minutes or --until")
        sys.exit(2)
    if until is not None:
        now = datetime.now().astimezone()
        try:
            target = datetime.strptime(until, "%H:%M").replace(
                year=now.year, month=now.month, day=now.day, tzinfo=now.tzinfo
            )
        except ValueError:
            click.echo("Invalid time format; use HH:MM")
            sys.exit(2)
        if target <= now:
            target += timedelta(days=1)
        minutes = int((target - now).total_seconds() // 60)
        debug(f"silence --until computed minutes={minutes} (target={target.isoformat()})")
    if minutes is None:  # pragma: no cover - defensive
        msg = "minutes not computed"
        raise RuntimeError(msg)
    if minutes <= 0:
        click.echo("Minutes must be > 0")
        sys.exit(2)
    until_dt = set_silence_for(minutes)
    click.secho(
        f"[bingbong] Silenced until {until_dt.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}",
        fg="blue",
    )
    debug("silence: set OK")


@cli.command()
def resume() -> None:
    """Resume chimes immediately by clearing silence state."""
    _require_darwin()
    with contextlib.suppress(FileNotFoundError):
        silence_path().unlink()
    click.secho("[bingbong] Silence cleared", fg="green")
    debug("resume: cleared silence file (if existed)")


@cli.command()
def doctor() -> None:
    """Run platform/player/config/plist checks."""
    _require_darwin()
    ok = True
    if not AFPLAY.exists() or not os.access(AFPLAY, os.X_OK):
        click.secho(f"Player missing or not executable: {AFPLAY}", fg="red")
        ok = False
    if config_path().exists():
        click.secho("Config present ✅", fg="green")
    else:
        click.secho(f"Config missing at {config_path()}", fg="yellow")
    plist = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    if plist.exists():
        click.secho("Plist present ✅", fg="green")
    else:
        click.secho("Plist missing ❌", fg="yellow")
    if not ok:
        sys.exit(1)
    debug("doctor: completed checks")


@cli.command()
def tick() -> None:
    """Decides what to play & respects silence windows.

    Called by launchd at :00/:15/:30/:45.
    """
    _require_darwin()
    debug("tick: start")
    if silence_active():
        debug("tick: skipped (silenced)")
        return

    cfg = Config.load()
    now_local = datetime.now().astimezone()
    debug(f"tick: now={now_local.isoformat()}")
    if _quiet_hours_active(now_local):
        debug("tick: skipped (quiet hours)")
        return
    pop_count, do_chime = compute_pop_count(now_local.minute, now_local.hour)
    if pop_count == 0:
        debug("tick: skipped (not a chime time)")
        return
    start_minute = now_local.minute
    if do_chime:
        debug("tick: playing chime")
        play_once(cfg.chime_wav)
        time.sleep(CHIME_DELAY)
        if datetime.now().astimezone().minute != start_minute:
            debug("tick: minute changed after chime; skipping pops to avoid drift")
            return
    debug(f"tick: playing {pop_count} pop(s)")
    play_repeated(cfg.pop_wav, pop_count, delay=POP_DELAY)
    debug("tick: done")


def main() -> None:
    """Compatibility entry point for `pyproject.toml` (`bingbong.cli:main`)."""
    # "call the Click group" pattern
    cli()
