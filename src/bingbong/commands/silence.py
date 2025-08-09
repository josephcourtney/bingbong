from __future__ import annotations

from datetime import datetime, timedelta

import click

import bingbong.paths as _paths
from bingbong import state
from bingbong.console import ok


@click.command()
@click.option("--minutes", type=int)
@click.option("--until", "until", type=str)
@click.pass_context
def silence(ctx: click.Context, minutes: int | None, until: str | None) -> None:
    """Pause or resume chimes."""
    outdir = _paths.ensure_outdir()
    now = datetime.now().astimezone()
    data = state.load(outdir)

    if minutes is not None and until:
        msg = "Cannot combine --minutes with --until"
        raise click.UsageError(msg)

    if minutes is None and not until:
        if data.get("pause_until"):
            if ctx.obj.get("dry_run"):
                ok("DRY RUN: would remove pause file")
            else:
                data.pop("pause_until", None)
                state.save(outdir, data)
            ok("\N{BELL} Chimes resumed.")
            return
        msg = "Specify --minutes or --until"
        raise click.UsageError(msg)

    if until:
        expiry = datetime.fromisoformat(until)
    else:
        if minutes is None:
            msg = f"Cannot convert {until=} to a datetime"
            raise ValueError(msg)
        expiry = now + timedelta(minutes=minutes)

    if ctx.obj.get("dry_run"):
        ok(f"DRY RUN: would pause until {expiry:%Y-%m-%d %H:%M}")
        return

    data["pause_until"] = expiry.isoformat()
    state.save(outdir, data)
    ok(f"🔕 Chimes paused until {expiry:%Y-%m-%d %H:%M}")
