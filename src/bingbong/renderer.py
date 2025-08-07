from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence


class PlistRenderer(Protocol):
    """Render a launchd plist from minute schedules."""

    def render(self, base: Sequence[str], extra: Sequence[str], template: str) -> str: ...


class MinimalRenderer:
    """Render StartCalendarInterval minutes into an existing plist template."""

    # NOTE: template *must* contain the placeholder <!--START_INTERVALS-->
    PLACEHOLDER = "<!--START_INTERVALS-->"

    @staticmethod
    def render(base: Sequence[str], extra: Sequence[str], template: str) -> str:
        """Inject <dict>…</dict> blocks into the placeholder inside *template*."""
        blocks = "".join(f"<dict><key>Minute</key><integer>{m}</integer></dict>" for m in [*base, *extra])
        snippet = f"<key>StartCalendarInterval</key><array>{blocks}</array>"
        #  ── Replace placeholder instead of naïve concatenation
        if MinimalRenderer.PLACEHOLDER not in template:
            msg = "template missing START_INTERVALS placeholder"
            raise ValueError(msg)
        return template.replace(MinimalRenderer.PLACEHOLDER, snippet)


__all__ = ["MinimalRenderer", "PlistRenderer"]
