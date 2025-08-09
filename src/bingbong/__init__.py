"""Package initialization for bingbong."""

from importlib.metadata import version

from .errors import BingBongError

__all__ = ["BingBongError", "__version__"]

__version__ = version("bingbong")
