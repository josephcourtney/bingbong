import contextlib
import re
import shutil
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import click
from click.shell_completion import get_completion_class
from tomlkit import dumps

from . import console, launchctl, notify
from .commands import build as build_cmd
from .commands import doctor as doctor_cmd
from .commands import logs_cmd
from .commands import silence as silence_cmd
from .commands import status as status_cmd
from .paths import config_path, ensure_outdir
from .scheduler import ChimeScheduler
from .utils import dryable

pkg_version_str = "0.0.0"
with contextlib.suppress(PackageNotFoundError):
    pkg_version_str = pkg_version("bingbong")


def get_input(prompt: str) -> str:
    """Small indirection over `input()` so tests can monkeypatch it."""
    return input(prompt)


@click.group()
@click.option("--dry-run", is_flag=True, help="Simulate actions without changes.")
@click.version_option(pkg_version_str)
@click.pass_context
def main(ctx: click.Context, *, dry_run: bool) -> None:
    """Time-based macOS notifier."""
    ctx.ensure_object(dict)
    console.setup_logging()
    ctx.obj["dry_run"] = dry_run


@main.command()
@click.option("--exit-timeout", type=int)
@click.option("--throttle-interval", type=int)
@click.option("--successful-exit/--no-successful-exit", default=None)
@click.option("--crashed/--no-crashed", default=None)
@click.option("--backoff", type=int, help="Seconds to back off on failure")
@click.pass_context
@dryable("would install launchctl job")
def install(  # noqa: C901
    _ctx: click.Context,
    *,
    exit_timeout: int | None,
    throttle_interval: int | None,
    successful_exit: bool | None,
    crashed: bool | None,
    backoff: int | None,
) -> None:
    """Install launchctl job."""
    if backoff is not None and successful_exit is not None:
        msg = "Cannot combine --backoff with --successful-exit/--no-successful-exit"
        raise click.UsageError(msg)

    cfg = ChimeScheduler(
        exit_timeout=exit_timeout,
        throttle_interval=throttle_interval,
        successful_exit=successful_exit,
        crashed=crashed,
    )
    if backoff is not None:
        cfg.throttle_interval = backoff
        cfg.crashed = True
    while True:
        try:
            launchctl.install(cfg)
        except FileExistsError as e:
            path = Path(e.filename or str(e))
            if click.confirm(f"{path} exists. Replace?", default=False):
                try:
                    path.unlink()
                except OSError as err:
                    console.err(f"Failed to remove {path}: {err}")
                    if not click.confirm("Retry installation?", default=False):
                        return
                else:
                    continue
            else:
                console.warn("Installation aborted.")
                return
        except Exception as e:  # noqa: BLE001 - show any error
            if click.confirm(f"Error: {e}. Retry?", default=False):
                continue
            console.warn("Installation aborted.")
            return
        break
    console.ok(f"Installed launchctl job (ThrottleInterval={cfg.throttle_interval}, Crashed={cfg.crashed}).")


@main.command()
@click.pass_context
@dryable("would uninstall launchctl job")
def uninstall(_ctx: click.Context) -> None:
    """Remove launchctl job."""
    launchctl.uninstall()
    console.ok("Uninstalled launchctl job.")


@main.command()
@click.pass_context
def clean(ctx: click.Context) -> None:
    """Delete generated audio files."""
    outdir = ensure_outdir()
    if outdir.exists():
        if ctx.obj.get("dry_run"):
            console.ok(f"DRY RUN: would remove {outdir}")
        else:
            shutil.rmtree(outdir)
            console.ok(f"Removed: {outdir}")
    else:
        console.warn("No generated files found.")


@main.command()
@click.pass_context
@dryable("would play chime")
def chime(_ctx: click.Context) -> None:
    """Play the appropriate chime for the current time."""
    notify.on_wake()
    notify.check_config_reload()
    notify.notify_time()
    console.ok("Chime played.")


@main.command()
def configure():
    """Interactive wizard to write config.toml."""
    cfg_path = config_path()

    click.echo("Chimes run on the quarter-hour (00, 15, 30, 45).")

    suppress_list: list[str] = []
    click.echo("Enable suppression windows? (y/n)")
    if get_input("> ").lower().startswith("y"):
        while True:
            click.echo("Enter suppression window as HH:MM-HH:MM:")
            rng = get_input("> ").strip()
            if not re.match(r"^[0-2]\d:[0-5]\d\s*-\s*[0-2]\d:[0-5]\d$", rng):
                console.err("Invalid time range")
                raise SystemExit(1)
            rng_norm = re.sub(r"\s*-\s*", "-", rng.strip())
            suppress_list.append(rng_norm)
            click.echo("Add another suppression window? (y/n)")
            if not get_input("> ").lower().startswith("y"):
                break

    click.echo("Respect Do Not Disturb? (y/n)")
    respect = get_input("> ").lower().startswith("y")

    click.echo("Enter timezone:")
    tz = get_input("> ").strip()
    try:
        ZoneInfo(tz)
    except ZoneInfoNotFoundError:
        console.err("Invalid timezone")
        raise SystemExit(1) from None

    click.echo("Enter custom sound paths, comma-separated:")
    raw_paths = [p.strip() for p in get_input("> ").split(",") if p.strip()]
    invalid = [p for p in raw_paths if not Path(p).is_file()]
    if invalid:
        console.err(f"Invalid sound paths: {', '.join(invalid)}")
        raise SystemExit(1)
    paths = raw_paths

    cfg = {
        "suppress_schedule": suppress_list,
        "respect_dnd": respect,
        "timezone": tz,
        "custom_sounds": paths,
    }
    cfg_path.write_text(dumps(cfg))
    console.ok(f"Wrote configuration to {cfg_path}")


main.add_command(build_cmd)
main.add_command(doctor_cmd)
main.add_command(logs_cmd)
main.add_command(silence_cmd)
main.add_command(status_cmd)


@main.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]), required=False)
def completion(shell: str | None = None) -> None:
    """Generate shell completion script."""
    shell = shell or "bash"
    cls = get_completion_class(shell)
    if cls is None:
        msg = "Unsupported shell"
        raise click.BadParameter(msg)
    script = cls(main, {}, "bingbong", "_BINGBONG_COMPLETE").source()
    click.echo(script)
