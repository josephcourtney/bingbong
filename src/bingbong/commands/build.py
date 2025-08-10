from __future__ import annotations

import click

from bingbong import audio
from bingbong.console import err, ok
from bingbong.errors import BingBongError
from bingbong.utils import dryable


@click.command()
@click.pass_context
@dryable("would build audio files")
def build(_ctx: click.Context) -> None:
    """Populate chime/quarter/hour audio files from packaged assets."""
    try:
        audio.build_all()
        ok("Built chime and quarter audio files.")
    except (BingBongError, RuntimeError) as e:
        err(str(e))
