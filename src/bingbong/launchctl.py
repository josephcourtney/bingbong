"""Thin wrappers around launchctl operations."""

from bingbong.scheduler import ChimeScheduler
from bingbong.service import install as service_install
from bingbong.service import uninstall as service_uninstall


def install(cfg: ChimeScheduler | None = None) -> None:
    """Install the launchd service."""
    service_install(cfg)


def uninstall() -> None:
    """Remove the launchd service."""
    service_uninstall()
