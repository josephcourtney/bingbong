import logging
import re
import shutil
import tempfile
from importlib.metadata import version as pkg_version
from pathlib import Path

import click
from croniter import croniter
from rich.console import Console
from tomlkit import dumps

from . import launchctl, notify
from .commands import (
    build as build_cmd,
)
from .commands import (
    doctor as doctor_cmd,
)
from .commands import (
    logs_cmd,
)
from .commands import (
    silence as silence_cmd,
)
from .commands import (
    status as status_cmd,
)
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


main.add_command(build_cmd)
main.add_command(doctor_cmd)
main.add_command(logs_cmd)
main.add_command(silence_cmd)
main.add_command(status_cmd)
