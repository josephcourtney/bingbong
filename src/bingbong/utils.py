"""Utility helpers for bingbong."""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Concatenate, ParamSpec, TypeVar

import click

if TYPE_CHECKING:
    from collections.abc import Callable

P = ParamSpec("P")
R = TypeVar("R")


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
