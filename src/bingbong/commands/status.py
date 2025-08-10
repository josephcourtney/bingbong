from __future__ import annotations

import shutil
import subprocess  # noqa: S404
import tomllib
from datetime import datetime, time

import click
from croniter import CroniterBadCronError, croniter

from bingbong.console import ok, warn
from bingbong.notify import is_paused
from bingbong.paths import config_path, ensure_outdir

PLIST_LABEL = "com.josephcourtney.bingbong"


@click.command()
def status() -> None:
    """Check whether the launchctl job is loaded and show schedule info."""
    launchctl_path = shutil.which("launchctl")
    if not launchctl_path:
        warn("launchctl not found in PATH.")
        return
    result = subprocess.run([launchctl_path, "list"], capture_output=True, text=True, check=False)  # noqa: S603
    if PLIST_LABEL in result.stdout:
        ok("\N{WHITE HEAVY CHECK MARK} Service is loaded.")
    else:
        warn("\N{BALLOT BOX WITH X} Service is NOT loaded.")

    outdir = ensure_outdir()
    cfg_path = config_path()
    if not cfg_path.exists():
        return

    cfg = tomllib.loads(cfg_path.read_text())
    expr = cfg.get("chime_schedule", "")
    now = datetime.now().astimezone()

    try:
        nxt = croniter(expr, now).get_next(datetime)
        ok(f"Next chime: {nxt:%Y-%m-%d %H:%M} (local)")  # "include date for clarity"
    except (CroniterBadCronError, ValueError):
        ok("Invalid cron in configuration")

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
