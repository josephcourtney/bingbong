from os import getenv
from pathlib import Path

from .errors import BingBongError

XDG_DATA_HOME = Path(getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
DEFAULT_OUTDIR = XDG_DATA_HOME / "bingbong"

XDG_CONFIG_HOME = Path(getenv("XDG_CONFIG_HOME", Path.home() / ".config"))


def ensure_outdir() -> Path:
    try:
        DEFAULT_OUTDIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        msg = f"Unable to create data directory at {DEFAULT_OUTDIR}: {e}"
        raise BingBongError(msg) from e
    return DEFAULT_OUTDIR


def config_path() -> Path:
    cfg_dir = XDG_CONFIG_HOME / "bingbong"
    try:
        cfg_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        msg = f"Unable to create config directory at {cfg_dir}: {e}"
        raise BingBongError(msg) from e
    return cfg_dir / "config.toml"
