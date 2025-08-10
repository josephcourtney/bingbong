from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Final

import click

__all__ = ["debug", "set_verbose", "verbose"]

_ENV_FLAG: Final[str] = "BINGBONG_VERBOSE"

_state = SimpleNamespace(verbose=False)


def set_verbose(*, value: bool | None = None) -> None:
    """Enable or disable verbose logs for this process.

    If ``value`` is None, enable when the environment flag is set.
    """
    if value is None:
        _state.verbose = os.environ.get(_ENV_FLAG, "") not in {"", "0", "false", "False"}
    else:
        _state.verbose = bool(value)


def verbose() -> bool:
    return _state.verbose


def debug(msg: str) -> None:
    """Emit a debug line when verbosity is enabled."""
    if _state.verbose:
        click.echo(f"[bingbong] {msg}")
