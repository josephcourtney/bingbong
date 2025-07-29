from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import click

from ..paths import ensure_outdir
from ..console import ok


@click.command()
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
                ok("DRY RUN: would remove pause file")
            else:
                pause_file.unlink()
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

    pause_file.write_text(expiry.isoformat())
    ok(f"🔕 Chimes paused until {expiry:%Y-%m-%d %H:%M}")
