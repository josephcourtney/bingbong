"""Package initialization for bingbong."""

from importlib.metadata import PackageNotFoundError, version

from .errors import BingBongError

__all__ = ["BingBongError", "__version__"]

try:  # pragma: no cover - tiny helper
    __version__ = version("bingbong")
except PackageNotFoundError:  # pragma: no cover - during development
    __version__ = "0.0.0"
