from __future__ import annotations

import shutil
import subprocess  # noqa: S404

import click

import bingbong.ffmpeg as _ffmpeg
import bingbong.paths as _paths
from bingbong.console import err, ok, warn


@click.command()
def doctor() -> None:
    """Run diagnostics to verify setup and health."""
    click.echo("Running diagnostics on bingbong.")

    launchctl_path = shutil.which("launchctl")
    if not launchctl_path:
        err("launchctl not found in PATH.")
        raise SystemExit(1)

    result = subprocess.run([launchctl_path, "list"], capture_output=True, text=True, check=False)  # noqa: S603
    loaded = "com.josephcourtney.bingbong" in result.stdout
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

    if _ffmpeg.ffmpeg_available():
        ok("FFmpeg is available")
    else:
        warn("FFmpeg cannot be found. Is it installed?")

    ok(
        "Hooray! All systems go."
        if loaded and not missing and _ffmpeg.ffmpeg_available()
        else "Woe! One or more checks failed."
    )
    raise SystemExit(0 if loaded and not missing and _ffmpeg.ffmpeg_available() else 1)
