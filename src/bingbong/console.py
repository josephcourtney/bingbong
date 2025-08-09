from __future__ import annotations

import logging

from rich.console import Console
from rich.text import Text

__all__ = ["err", "get_console", "ok", "setup_logging", "warn"]

_default_console = Console()


def get_console(*, no_color: bool = False) -> Console:
    """Return a Console instance respecting ``no_color``."""
    if no_color:
        return Console(color_system=None)
    return _default_console


def ok(message: str, *, no_color: bool = False) -> None:
    get_console(no_color=no_color).print(Text(message, style="green"))


def warn(message: str, *, no_color: bool = False) -> None:
    get_console(no_color=no_color).print(Text(message, style="yellow"))


def err(message: str, *, no_color: bool = False) -> None:
    get_console(no_color=no_color).print(Text(message, style="red"))


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logging with a standard format."""
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
