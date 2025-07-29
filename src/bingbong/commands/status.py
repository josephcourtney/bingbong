from __future__ import annotations

import subprocess  # noqa: S404
import shutil
import tomllib
from datetime import datetime
from croniter import CroniterBadCronError, croniter

import click

from ..notify import is_paused
from ..paths import ensure_outdir
from ..console import ok

PLIST_LABEL = "com.josephcourtney.bingbong"


@click.command()
def status() -> None:
    """Check whether the launchctl job is loaded and show schedule info."""
    launchctl_path = shutil.which("launchctl")
    result = subprocess.run([launchctl_path, "list"], capture_output=True, text=True, check=False)
    if PLIST_LABEL in result.stdout:
        ok("\N{WHITE HEAVY CHECK MARK} Service is loaded.")
    else:
        ok("\N{BALLOT BOX WITH X} Service is NOT loaded.")

    outdir = ensure_outdir()
    cfg_path = outdir / "config.toml"
    if not cfg_path.exists():
        return

    cfg = tomllib.loads(cfg_path.read_text())
    expr = cfg.get("chime_schedule", "")
    now = datetime.now().astimezone()

    try:
        nxt = croniter(expr, now).get_next(datetime)
        ok(f"Next chime: {nxt:%H:%M}")
    except (CroniterBadCronError, ValueError):
        ok("Invalid cron in configuration")

    for rng in cfg.get("suppress_schedule", []):
        start_s, end_s = rng.split("-")
        st = datetime.strptime(start_s, "%H:%M").time()  # noqa: DTZ007
        en = datetime.strptime(end_s, "%H:%M").time()  # noqa: DTZ007
        if st <= now.time() <= en:
            ok(f"Suppressed until {en:%H:%M}")

    pause_until = is_paused(outdir, now)
    if pause_until:
        ok(f"Chimes paused until {pause_until:%Y-%m-%d %H:%M}")
