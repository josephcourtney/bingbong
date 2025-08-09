"""Utility helpers for bingbong."""

from __future__ import annotations

import functools
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Concatenate, ParamSpec, TypeVar

import click

if TYPE_CHECKING:
    from collections.abc import Callable

P = ParamSpec("P")
R = TypeVar("R")


def _atomic_replace(tmp_path: Path, dest: Path) -> None:
    """Cross-platform, atomic-ish replace of tmp file with dest.

    Falls back to best effort if OS doesn't support true atomicity.
    """
    Path(str(tmp_path)).replace(str(dest))


def atomic_write_text(path: Path, data: str) -> None:
    """Write text atomically to ``path`` (UTF-8)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent) as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
        tmp = Path(fh.name)
    _atomic_replace(tmp, path)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write bytes atomically to ``path``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("wb", delete=False, dir=path.parent) as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
        tmp = Path(fh.name)
    _atomic_replace(tmp, path)


def dryable(
    message: str,
) -> Callable[
    [Callable[Concatenate[click.Context, P], R]], Callable[Concatenate[click.Context, P], R | None]
]:
    """Skip command execution when ``--dry-run`` is set.

    Parameters
    ----------
    message:
        Description of the action that would have been performed.
    """

    def decorator(
        func: Callable[Concatenate[click.Context, P], R],
    ) -> Callable[Concatenate[click.Context, P], R | None]:
        @functools.wraps(func)
        def wrapper(ctx: click.Context, *args: P.args, **kwargs: P.kwargs) -> R | None:
            if ctx.obj.get("dry_run"):
                click.echo(f"DRY RUN: {message}")
                return None
            return func(ctx, *args, **kwargs)

        return wrapper

    return decorator
