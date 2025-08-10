from __future__ import annotations

import os
import subprocess  # noqa: S404
import time
from pathlib import Path

# macOS default player (we only ever execute a fixed binary with a file path)
AFPLAY = Path(os.environ.get("BINGBONG_PLAYER", "/usr/bin/afplay"))


def play_once(path: str) -> None:
    # We keep this simple & robust for launchd: no extra deps, just afplay.
    # Paths are controlled by the user/config; we do not pass shell=True.
    subprocess.run([AFPLAY, path], check=False)  # noqa: S603


def play_repeated(path: str, times: int, delay: float = 0.2) -> None:
    for _ in range(times):
        play_once(path)
        time.sleep(delay)
