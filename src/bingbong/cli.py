from __future__ import annotations

import json
import os
import subprocess  # noqa: S404
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from importlib import resources
from pathlib import Path

import click
from onginred.schedule import LaunchdSchedule
from onginred.service import LaunchdService

# --- Paths & constants --------------------------------------------------------

APP_NAME = "bingbong"
LABEL = "com.bingbong.chimes"  # change if you want a different launchd label


QUARTER_1 = 15
QUARTER_2 = 30
QUARTER_3 = 45

# macOS default player (we only ever execute a fixed binary with a file path)
AFPLAY = "/usr/bin/afplay"  # native on macOS


def _app_support() -> Path:
    """Return the application support directory (env override-aware)."""
    return Path(
        os.environ.get(
            "BINGBONG_APP_SUPPORT",
            str(Path.home() / "Library" / "Application Support" / APP_NAME),
        )
    )


def _config_path() -> Path:
    return _app_support() / "config.json"


def _silence_path() -> Path:
    return _app_support() / "silence_until.json"


# --- Config -------------------------------------------------------------------


@dataclass
class Config:
    chime_wav: str
    pop_wav: str

    @staticmethod
    def load() -> Config:
        cfg_path = _config_path()
        if not cfg_path.exists():
            click.echo(f"[bingbong] Missing config at {cfg_path}. Run: bingbong install ...", err=True)
            sys.exit(1)

        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        return Config(chime_wav=data["chime_wav"], pop_wav=data["pop_wav"])

    def save(self) -> None:
        app_dir = _app_support()
        app_dir.mkdir(parents=True, exist_ok=True)
        _config_path().write_text(
            json.dumps({"chime_wav": self.chime_wav, "pop_wav": self.pop_wav}, indent=2), encoding="utf-8"
        )


# --- Silence window -----------------------------------------------------------


def get_silence_until() -> datetime | None:
    path = _silence_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ts = data.get("until_epoch")
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts, tz=UTC)

    except (OSError, ValueError, json.JSONDecodeError):
        # Corrupt file or unreadable — ignore it.
        return None
    return None


def set_silence_for(minutes: int) -> datetime:
    app_dir = _app_support()
    app_dir.mkdir(parents=True, exist_ok=True)
    until = datetime.now(UTC) + timedelta(minutes=minutes)

    _silence_path().write_text(json.dumps({"until_epoch": until.timestamp()}, indent=2), encoding="utf-8")
    return until


def silence_active(now: datetime | None = None) -> bool:
    until = get_silence_until()
    if not until:
        return False
    now = now or datetime.now(UTC)
    return now < until


# --- Audio --------------------------------------------------------------------


def play_once(path: str) -> None:
    # We keep this simple & robust for launchd: no extra deps, just afplay.
    # Paths are controlled by the user/config; we do not pass shell=True.
    subprocess.run([AFPLAY, path], check=False)  # noqa: S603


def play_repeated(path: str, times: int, delay: float = 0.2) -> None:
    for _ in range(times):
        play_once(path)
        time.sleep(delay)


# --- The “tick” that launchd runs --------------------------------------------


def compute_pop_count(minute: int, hour_24: int) -> tuple[int, bool]:
    """Return `(pop_count, do_chime_first)`.

    - On the hour: chime first, then 1..12 pops for the hour.


    - :15 -> 1 pop, :30 -> 2 pops, :45 -> 3 pops.
    - Otherwise -> (0, False).
    """
    if minute == 0:
        h12 = hour_24 % 12 or 12
        return h12, True

    if minute == QUARTER_1:
        return 1, False

    if minute == QUARTER_2:
        return 2, False

    if minute == QUARTER_3:
        return 3, False
    return 0, False


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


# --- Service management (using onginred) --------------------------------------


# We build a fixed StartCalendarInterval set for :00/:15/:30/:45 across 24h.
def _build_schedule() -> LaunchdSchedule:
    sched = LaunchdSchedule()
    # Every hour at minute 0/15/30/45 (24h)
    for h in range(24):
        for m in (0, QUARTER_1, QUARTER_2, QUARTER_3):
            sched.time.add_calendar_entry(hour=h, minute=m)
    # We don't need KeepAlive; launchd will trigger us at the times above.
    return sched


def _service(plist_path: str | None, program_args: list[str]) -> LaunchdService:
    return LaunchdService(
        bundle_identifier=LABEL,
        command=program_args,  # ProgramArguments
        schedule=_build_schedule(),
        plist_path=plist_path,  # None -> ~/Library/LaunchAgents/<label>.plist
        # We let logs go to defaults (/var/log/<label>.out/.err)
        launchctl=None,
    )


# --- CLI commands -------------------------------------------------------------


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
    python = sys.executable
    args = [python, "-m", APP_NAME, "tick"]
    svc = _service(plist_path, args)

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
    python = sys.executable
    args = [python, "-m", APP_NAME, "tick"]
    svc = _service(plist_path, args)
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

    if _config_path().exists():
        cfg = Config.load()
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


@cli.command(hidden=True)
def tick() -> None:
    """Decides what to play & respects silence windows.

    Called by launchd at :00/:15/:30/:45.
    """
    # If silenced, exit quietly
    if silence_active():
        return

    cfg = Config.load()
    now_local = datetime.now(tz=UTC)  # local wall clock
    pop_count, do_chime = compute_pop_count(now_local.minute, now_local.hour)

    if pop_count == 0:
        return

    if do_chime:
        play_once(cfg.chime_wav)
        time.sleep(0.25)

    play_repeated(cfg.pop_wav, pop_count, delay=0.18)


# Allow `python -m bingbong ...`
def main():
    cli()
