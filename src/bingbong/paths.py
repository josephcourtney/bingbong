from os import getenv
from pathlib import Path

XDG_DATA_HOME = Path(getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
DEFAULT_OUTDIR = XDG_DATA_HOME / "bingbong"

XDG_CONFIG_HOME = Path(getenv("XDG_CONFIG_HOME", Path.home() / ".config"))


def ensure_outdir() -> Path:
    DEFAULT_OUTDIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_OUTDIR


def config_path() -> Path:
    cfg_dir = XDG_CONFIG_HOME / "bingbong"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "config.toml"
