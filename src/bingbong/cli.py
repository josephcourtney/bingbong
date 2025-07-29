import logging
import re
import shutil
import subprocess  # noqa: S404
import tempfile
import time
import tomllib
from datetime import datetime, timedelta
from importlib.metadata import version as pkg_version
from pathlib import Path

import click
from croniter import CroniterBadCronError, croniter
from rich.console import Console
from rich.text import Text
from tomlkit import dumps

from . import audio, launchctl, notify
from .ffmpeg import ffmpeg_available
from .notify import is_paused
from .paths import ensure_outdir

LOG_ROTATE_SIZE = 10 * 1024 * 1024  # rotate logs larger than 10 MB

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

console = Console()


@click.group()
@click.option("--dry-run", is_flag=True, help="Simulate actions without changes.")
@click.version_option(pkg_version("bingbong"))
@click.pass_context
def main(ctx: click.Context, *, dry_run: bool) -> None:
    """Time-based macOS notifier."""
    ctx.ensure_object(dict)
    ctx.obj["dry_run"] = dry_run


@main.command()
@click.pass_context
def build(ctx: click.Context) -> None:
    """Build composite chime/quarter audio files."""
    if not ffmpeg_available():
        click.echo("ffmpeg is not available")
        return
    if ctx.obj.get("dry_run"):
        click.echo("DRY RUN: would build audio files")
        return
    try:
        audio.build_all()
        logger.info("Built chime and quarter audio files.")
    except RuntimeError as err:
        click.echo(str(err))


@main.command()
@click.pass_context
def install(ctx: click.Context) -> None:
    """Install launchctl job."""
    if ctx.obj.get("dry_run"):
        click.echo("DRY RUN: would install launchctl job")
        return
    launchctl.install()
    click.echo("Installed launchctl job.")


@main.command()
@click.pass_context
def uninstall(ctx: click.Context) -> None:
    """Remove launchctl job."""
    if ctx.obj.get("dry_run"):
        click.echo("DRY RUN: would uninstall launchctl job")
        return
    launchctl.uninstall()
    click.echo("Uninstalled launchctl job.")


@main.command()
@click.pass_context
def clean(ctx: click.Context) -> None:
    """Delete generated audio files."""
    outdir = ensure_outdir()
    if outdir.exists():
        if ctx.obj.get("dry_run"):
            click.echo(f"DRY RUN: would remove {outdir}")
        else:
            shutil.rmtree(outdir)
            click.echo(f"Removed: {outdir}")
    else:
        click.echo("No generated files found.")


@main.command()
@click.pass_context
def chime(ctx: click.Context) -> None:
    """Play the appropriate chime for the current time."""
    if ctx.obj.get("dry_run"):
        click.echo("DRY RUN: would play chime")
        return
    notify.notify_time()
    click.echo("Chime played.")


@main.command()
def configure():
    """Interactive wizard to write config.toml."""
    outdir = ensure_outdir()
    cfg_path = outdir / "config.toml"

    click.echo("Enter cron expression for chime schedule:")
    cron_expr = input().strip()
    if not croniter.is_valid(cron_expr):
        click.echo("Invalid cron")
        raise SystemExit(1)

    suppress_list: list[str] = []
    click.echo("Enable suppression windows? (y/n)")
    if input().lower().startswith("y"):
        while True:
            click.echo("Enter suppression window as HH:MM-HH:MM:")
            rng = input().strip()
            if not re.match(r"^[0-2]\d:[0-5]\d-[0-2]\d:[0-5]\d$", rng):
                click.echo("Invalid time range")
                raise SystemExit(1)
            suppress_list.append(rng)
            click.echo("Add another suppression window? (y/n)")
            if not input().lower().startswith("y"):
                break

    click.echo("Respect Do Not Disturb? (y/n)")
    respect = input().lower().startswith("y")

    click.echo("Enter timezone:")
    tz = input().strip()

    click.echo("Enter custom sound paths, comma-separated:")
    paths = [p.strip() for p in input().split(",") if p.strip()]

    cfg = {
        "chime_schedule": cron_expr,
        "suppress_schedule": suppress_list,
        "respect_dnd": respect,
        "timezone": tz,
        "custom_sounds": paths,
    }
    cfg_path.write_text(dumps(cfg))
    click.echo(f"Wrote configuration to {cfg_path}")


@main.command()
def status():
    """Check whether the launchctl job is loaded and show schedule info."""
    # 1) Service load state
    launchctl_path = shutil.which("launchctl")
    result = subprocess.run([launchctl_path, "list"], capture_output=True, text=True, check=False)  # noqa: S603
    if PLIST_LABEL in result.stdout:
        click.echo("✅ Service is loaded.")
    else:
        click.echo("❌ Service is NOT loaded.")

    # 2) If user has a config, show next-run and suppression/pause info
    outdir = ensure_outdir()
    cfg_path = outdir / "config.toml"
    if not cfg_path.exists():
        return

    cfg = tomllib.loads(cfg_path.read_text())
    expr = cfg.get("chime_schedule", "")
    now = datetime.now().astimezone()

    # Next scheduled chime
    try:
        nxt = croniter(expr, now).get_next(datetime)
        click.echo(f"Next chime: {nxt:%H:%M}")
    except (CroniterBadCronError, ValueError):
        click.echo("Invalid cron in configuration")

    # Scheduled suppression windows
    for rng in cfg.get("suppress_schedule", []):
        start_s, end_s = rng.split("-")
        st = datetime.strptime(start_s, "%H:%M").time()  # noqa: DTZ007
        en = datetime.strptime(end_s, "%H:%M").time()  # noqa: DTZ007
        if st <= now.time() <= en:
            click.echo(f"Suppressed until {en:%H:%M}")

    # Manual pause
    pause_until = is_paused(outdir, now)
    if pause_until:
        click.echo(f"Chimes paused until {pause_until:%Y-%m-%d %H:%M}")


def _print_log(log: Path, *, lines: int | None, follow: bool, console: Console) -> None:
    if not log.exists():
        console.print(Text("WARN: No log found.", style="yellow"))
        return

    def read_tail(path: Path, n: int) -> list[str]:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return f.readlines()[-n:]

    def print_lines(lines: list[str]) -> None:
        for line in lines:
            console.print(Text("OK: ", style="green") + line.rstrip())

    if follow:
        console.print(Text(f"Following {log}", style="cyan"))
        with log.open("r", encoding="utf-8", errors="replace") as f:
            f.seek(0, 2)  # seek to end
            while True:
                line = f.readline()
                if line:
                    console.print(Text("OK: ", style="green") + line.rstrip())
                else:
                    time.sleep(0.5)
    else:
        all_lines = (
            read_tail(log, lines) if lines else log.read_text(encoding="utf-8", errors="replace").splitlines()
        )
        print_lines(all_lines)


@main.command()
@click.option("--clear", is_flag=True, help="Clear log files instead of displaying them.")
@click.option("--lines", type=int, help="Show only the last N lines of each log.")
@click.option("--follow", is_flag=True, help="Stream appended lines in real-time.")
@click.option("--no-color", is_flag=True, help="Disable color output.")
def logs(*, clear: bool, lines: int | None, follow: bool, no_color: bool) -> None:
    """Display or clear the latest logs for the launchctl job."""
    for log in [STDOUT_LOG, STDERR_LOG]:
        console.print(f"\n[bold underline]{log}[/]")
        if clear:
            if log.exists():
                log.unlink()
                console.print(Text("OK: Cleared.", style="green"))
            else:
                console.print(Text("WARN: No log to clear.", style="yellow"))
        else:
            _print_log(log, lines=lines, follow=follow, console=console)


@main.command()
@click.option("--minutes", type=int)
@click.option("--until", "until", type=str)
@click.pass_context
def silence(ctx: click.Context, minutes: int | None, until: str | None) -> None:
    """Pause or resume chimes."""
    outdir = ensure_outdir()
    pause_file = outdir / ".pause_until"
    now = datetime.now().astimezone()

    if minutes is not None and until:
        msg = "Cannot combine --minutes with --until"
        raise click.UsageError(msg)

    if minutes is None and not until:
        if pause_file.exists():
            if ctx.obj.get("dry_run"):
                click.echo("DRY RUN: would remove pause file")
            else:
                pause_file.unlink()
            click.echo("🔔 Chimes resumed.")
            return
        msg = "Specify --minutes or --until"
        raise click.UsageError(msg)

    expiry: datetime
    if until:
        expiry = datetime.fromisoformat(until)
    else:
        if minutes is None:
            msg = f"Cannot convert {until=} to a datetime"
            raise ValueError(msg)
        expiry = now + timedelta(minutes=minutes)

    if ctx.obj.get("dry_run"):
        click.echo(f"DRY RUN: would pause until {expiry:%Y-%m-%d %H:%M}")
        return

    pause_file.write_text(expiry.isoformat())
    click.echo(f"🔕 Chimes paused until {expiry:%Y-%m-%d %H:%M}")


def _check_launchctl():
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
    return PLIST_LABEL in result.stdout


def _check_audio_assets(outdir: Path) -> list[Path]:
    # Check audio files
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
    return sorted(required_files - existing_files)


@main.command()
def doctor():
    """Run diagnostics to verify setup and health."""
    click.echo("Running diagnostics on bingbong.")

    plist_loaded = _check_launchctl()
    if plist_loaded:
        click.echo("[x] launchctl job is loaded.")
    else:
        click.echo("[ ] launchctl job is NOT loaded.")
        click.echo("    try running `bingbong install` to load it.")

    outdir = ensure_outdir()

    missing_audio_files = _check_audio_assets(outdir)
    if not missing_audio_files:
        click.echo(f"[x] All required audio files are present in {outdir}")
    else:
        click.echo(f"[ ] Missing audio files in {outdir}:")
        for f in missing_audio_files:
            click.echo(f"   - {f}")
        click.echo("    if FFmpeg is installed, run `bingbong build` to create them.")

    if ffmpeg_available():
        click.echo("[x] FFmpeg is available")
    else:
        click.echo("[ ] FFmpeg cannot be found. Is it installed?")

    click.echo("")
    # 4) Logs directory and rotation
    logs = Path.home() / "Library" / "Logs"
    try:
        if logs.exists():
            # rotate if oversized
            main_log = logs / "bingbong.log"
            if main_log.exists() and main_log.stat().st_size > LOG_ROTATE_SIZE:
                rotated = logs / "bingbong.log.1"
                main_log.rename(rotated)
            # list all
            for f in sorted(logs.iterdir()):
                if f.name.startswith("bingbong.log"):
                    click.echo(f.name)
    except PermissionError:
        click.echo("cannot write logs")

    # final summary
    ok = plist_loaded and not missing_audio_files and ffmpeg_available()
    click.echo("Hooray! All systems go." if ok else "Woe! One or more checks failed.")
    raise SystemExit(0 if ok else 1)
