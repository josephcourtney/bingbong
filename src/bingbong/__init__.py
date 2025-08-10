"""Package initialization for bingbong."""

from importlib.metadata import PackageNotFoundError, version

try:  # pragma: no cover - tiny helper
    __version__ = version("bingbong")
except PackageNotFoundError:  # pragma: no cover - during development
    __version__ = "0.0.0"

__all__ = ["__version__"]
