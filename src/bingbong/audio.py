from __future__ import annotations

import os
import subprocess  # noqa: S404
import sys
import time
from pathlib import Path

import click

from bingbong.log import debug

# macOS default player (we only ever execute a fixed binary with a file path)
AFPLAY = Path(os.environ.get("BINGBONG_PLAYER", "/usr/bin/afplay"))

__all__ = ["AFPLAY", "play_once", "play_repeated"]


def play_once(path: str | Path) -> None:
    file_path = Path(path)
    if not file_path.is_file():
        click.secho(f"[bingbong] audio file not found: {file_path}", fg="red", err=True)
        sys.exit(1)
    debug(f"playing once: player={AFPLAY} file={file_path}")
    result = subprocess.run([AFPLAY, str(file_path)], check=False)  # noqa: S603
    if result.returncode != 0:
        click.secho(f"[bingbong] player exited with code {result.returncode}", fg="red", err=True)
        sys.exit(result.returncode)
    debug("play once: done (exit=0)")


def play_repeated(path: str | Path, times: int, delay: float = 0.2) -> None:
    debug(f"play repeated: times={times} delay={delay}")
    for _ in range(times):
        play_once(path)
        time.sleep(delay)
    debug("play repeated: done")
