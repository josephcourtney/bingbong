from os import getenv
from pathlib import Path


def ensure_outdir() -> Path:
    """Determine XDG_DATA_HOME at runtime, then ensure and return $XDG_DATA_HOME/bingbong."""
    base = Path(getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    out = base / "bingbong"
    out.mkdir(parents=True, exist_ok=True)
    return out
