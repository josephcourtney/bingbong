from __future__ import annotations

import tomllib
from datetime import datetime, time, timedelta

import click

from bingbong import service
from bingbong.console import ok, warn
from bingbong.notify import is_paused
from bingbong.paths import config_path, ensure_outdir

PLIST_LABEL = "com.josephcourtney.bingbong"
MIN_PER_HOUR = 60


@click.command()
def status() -> None:
    """Check whether the launchctl job is loaded and show schedule info."""
    if service.is_loaded():
        ok("\N{WHITE HEAVY CHECK MARK} Service is loaded.")
    else:
        warn("\N{BALLOT BOX WITH X} Service is NOT loaded.")

    outdir = ensure_outdir()
    cfg_path = config_path()
    if not cfg_path.exists():
        return

    cfg = tomllib.loads(cfg_path.read_text())
    now = datetime.now().astimezone()
    # compute next quarter-hour locally
    minute = now.minute
    next_min = next(m for m in (0, 15, 30, 45, 60) if m > minute)
    nxt = now.replace(second=0, microsecond=0)

    nxt = (
        nxt.replace(minute=0) + timedelta(hours=1)
        if next_min == MIN_PER_HOUR
        else nxt.replace(minute=next_min)
    )
    ok(f"Next chime: {nxt:%Y-%m-%d %H:%M} (local)")  # "include date for clarity"

    for rng in cfg.get("suppress_schedule", []):
        start_s, end_s = rng.split("-")
        st = datetime.strptime(start_s, "%H:%M").time()  # noqa: DTZ007
        en = datetime.strptime(end_s, "%H:%M").time()  # noqa: DTZ007
        # "handle overnight windows (e.g., 23:30-00:30)"
        tnow: time = now.time()
        in_window = (st <= tnow <= en) if st <= en else (tnow >= st or tnow <= en)
        if in_window:
            warn(f"Suppressed now (window {rng})")

    pause_until = is_paused(outdir, now)
    if pause_until:
        warn(f"Chimes paused until {pause_until:%Y-%m-%d %H:%M}")
