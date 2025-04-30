from os import getenv
from pathlib import Path

XDG_DATA_HOME = Path(getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
OUTDIR = XDG_DATA_HOME / "bingbong"
OUTDIR.mkdir(parents=True, exist_ok=True)
