from pathlib import Path

from platformdirs import PlatformDirs

from .errors import BingBongError

# Public aliases kept for test/back-compat while using platformdirs under the hood
_DIRS = PlatformDirs(appname="bingbong", appauthor=False)
DEFAULT_OUTDIR = Path(_DIRS.user_data_dir)
_CONFIG_DIR = Path(_DIRS.user_config_dir)


def ensure_outdir() -> Path:
    """Ensure and return the per-user data directory."""
    try:
        DEFAULT_OUTDIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        msg = f"Unable to create data directory at {DEFAULT_OUTDIR}: {e}"
        raise BingBongError(msg) from e
    return DEFAULT_OUTDIR


def config_path() -> Path:
    """Ensure and return the path to the user config file."""
    try:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        msg = f"Unable to create config directory at {_CONFIG_DIR}: {e}"
        raise BingBongError(msg) from e
    return _CONFIG_DIR / "config.toml"
