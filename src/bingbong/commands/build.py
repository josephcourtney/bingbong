from __future__ import annotations

import click

from bingbong import audio
from bingbong.console import err, ok
from bingbong.errors import BingBongError
from bingbong.ffmpeg import ffmpeg_available
from bingbong.utils import dryable


@click.command()
@click.pass_context
@dryable("would build audio files")
def build(_ctx: click.Context) -> None:
    """Build composite chime audio files."""
    if not ffmpeg_available():
        err("ffmpeg is not available")
        return
    try:
        audio.build_all()
        ok("Built chime and quarter audio files.")
    except (BingBongError, RuntimeError) as e:
        err(str(e))
