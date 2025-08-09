"""Thin wrappers around launchctl operations."""

import sys

from bingbong.scheduler import ChimeScheduler

if sys.platform == "darwin":
    from bingbong.service import install as service_install
    from bingbong.service import uninstall as service_uninstall

    def install(cfg: ChimeScheduler | None = None) -> None:
        """Install the launchd service."""
        service_install(cfg)

    def uninstall() -> None:
        """Remove the launchd service."""
        service_uninstall()

else:

    def install(_cfg: ChimeScheduler | None = None) -> None:
        """Install is only supported on macOS."""
        msg = "launchctl is only available on macOS"
        raise RuntimeError(msg)

    def uninstall() -> None:
        """Uninstall is only supported on macOS."""
        msg = "launchctl is only available on macOS"
        raise RuntimeError(msg)
