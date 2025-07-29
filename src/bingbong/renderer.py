from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence


class PlistRenderer(Protocol):
    """Render a launchd plist from minute schedules."""

    def render(self, base: Sequence[str], extra: Sequence[str], template: str) -> str: ...


class MinimalRenderer:
    """Simplest renderer that injects a StartCalendarInterval snippet."""

    @staticmethod
    def render(base: Sequence[str], extra: Sequence[str], template: str) -> str:
        snippet = "<key>StartCalendarInterval</key><array>"
        for m in [*base, *extra]:
            snippet += f"<dict><key>Minute</key><integer>{m}</integer></dict>"
        snippet += "</array>"
        return snippet + template


__all__ = ["MinimalRenderer", "PlistRenderer"]
