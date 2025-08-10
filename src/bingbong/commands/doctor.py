from __future__ import annotations

import shutil

import click

import bingbong.paths as _paths
from bingbong import service
from bingbong.console import err, ok, warn


@click.command()
def doctor() -> None:
    """Run diagnostics to verify setup and health."""
    click.echo("Running diagnostics on bingbong.")

    launchctl_path = shutil.which("launchctl")

    loaded = service.is_loaded()
    if not launchctl_path:
        err("launchctl not found in PATH.")
        raise SystemExit(1)

    click.echo("[x] launchctl job is loaded." if loaded else "[ ] launchctl job is NOT loaded.")

    outdir = _paths.ensure_outdir()
    missing = [
        name
        for name in [
            *(f"hour_{n}.wav" for n in range(1, 13)),
            "quarter_1.wav",
            "quarter_2.wav",
            "quarter_3.wav",
            "silence.wav",
        ]
        if not (outdir / name).exists()
    ]
    if missing:
        warn(f"Missing audio files in {outdir}: {', '.join(missing)}")
    else:
        ok(f"All required audio files are present in {outdir}")

    ok("Hooray! All systems go." if loaded and not missing else "Woe! One or more checks failed.")
    raise SystemExit(0 if loaded and not missing else 1)
