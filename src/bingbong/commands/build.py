from __future__ import annotations

import click

from bingbong import audio
from bingbong.console import err, ok
from bingbong.ffmpeg import ffmpeg_available


@click.command()
@click.pass_context
def build(ctx: click.Context) -> None:
    """Build composite chime audio files."""
    if not ffmpeg_available():
        err("ffmpeg is not available")
        return
    if ctx.obj.get("dry_run"):
        ok("DRY RUN: would build audio files")
        return
    try:
        audio.build_all()
        ok("Built chime and quarter audio files.")
    except RuntimeError as e:
        err(str(e))
