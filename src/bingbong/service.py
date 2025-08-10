import shutil
import subprocess  # noqa: S404
import sys
from typing import Final

import onginred.service as og_service
from onginred.service import LaunchdService

from bingbong import paths
from bingbong.scheduler import ChimeScheduler, render

LABEL: Final[str] = "com.josephcourtney.bingbong"


def _service(cfg: ChimeScheduler) -> LaunchdService:
    outdir = paths.ensure_outdir()
    return LaunchdService(
        bundle_identifier=LABEL,
        command=[sys.executable, "-m", "bingbong", "chime"],
        schedule=render(cfg),
        log_dir=outdir,
        log_name="bingbong",
        create_dir=True,
    )


def install(cfg: ChimeScheduler | None = None) -> None:
    _service(cfg or ChimeScheduler()).install()


def uninstall() -> None:
    _service(ChimeScheduler()).uninstall()


def is_loaded() -> bool:
    """Return True if the launchd job is currently loaded.

    Preference order:
      1) Use onginred's `LaunchctlClient().list()` if available.
      2) Fall back to `launchctl list` and grep for the label.
    """
    # 1) onginred client path
    try:
        client = og_service.LaunchctlClient()
        get_list = getattr(client, "list", None)
        if callable(get_list):
            listing = get_list()
            if isinstance(listing, dict):
                return LABEL in listing
            if hasattr(listing, "keys"):
                return LABEL in listing  # type: ignore[no-any-return]
    except (AttributeError, TypeError, ImportError):
        # If API is different than expected, fall through to shell probe
        pass

    # 2) shell fallback
    launchctl_path = shutil.which("launchctl")
    if not launchctl_path:
        return False
    result = subprocess.run([launchctl_path, "list"], capture_output=True, text=True, check=False)  # noqa: S603
    return LABEL in result.stdout
