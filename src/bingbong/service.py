import sys

from onginred.service import LaunchdService

from bingbong.paths import ensure_outdir
from bingbong.scheduler import ChimeScheduler, render

LABEL = "com.josephcourtney.bingbong"


def _service(cfg: ChimeScheduler) -> LaunchdService:
    outdir = ensure_outdir()
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
