from __future__ import annotations

import os
from typing import Final

import click

__all__ = ["set_verbose", "verbose", "debug"]

_VERBOSE: bool = False
_ENV_FLAG: Final[str] = "BINGBONG_VERBOSE"


def set_verbose(value: bool | None = None) -> None:
    """Enable or disable verbose logs for this process.

    If ``value`` is None, enable when the environment flag is set.
    """
    global _VERBOSE
    if value is None:
        _VERBOSE = os.environ.get(_ENV_FLAG, "") not in ("", "0", "false", "False")
    else:
        _VERBOSE = bool(value)


def verbose() -> bool:
    return _VERBOSE


def debug(msg: str) -> None:
    """Emit a debug line when verbosity is enabled."""
    if _VERBOSE:
        click.echo(f"[bingbong] {msg}")
