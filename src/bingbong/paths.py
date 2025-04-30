from os import getenv
from pathlib import Path

XDG_DATA_HOME = Path(getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
DEFAULT_OUTDIR = XDG_DATA_HOME / "bingbong"
DEFAULT_OUTDIR.mkdir(parents=True, exist_ok=True)  # still create it once
