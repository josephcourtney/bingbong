import sys

from onginred.schedule import LaunchdSchedule
from onginred.service import LaunchdService

from bingbong.paths import ensure_outdir
from bingbong.scheduler import ChimeScheduler

LABEL = "com.josephcourtney.bingbong"


def make_schedule(cfg: ChimeScheduler) -> LaunchdSchedule:
    sch = LaunchdSchedule()
    # Trigger at every hour for each chime minute
    for minute in cfg.minutes_for_chime():
        for hour in range(24):
            sch.time.add_calendar_entry(hour=hour, minute=minute)
    for rng in cfg.suppress_schedule:
        # cron “m h …” ⇒ convert to “HH:MM-HH:MM”
        m, *_ = rng.split()
        sch.time.add_suppression_window(f"{int(m):02d}:00-{int(m):02d}:00")
    sch.behavior.run_at_load = True
    sch.behavior.keep_alive = True
    return sch


def _service(cfg: ChimeScheduler) -> LaunchdService:
    outdir = ensure_outdir()
    return LaunchdService(
        bundle_identifier=LABEL,
        command=[sys.executable, "-m", "bingbong", "chime"],
        schedule=make_schedule(cfg),
        log_dir=outdir,
        log_name="bingbong",
        create_dir=True,
    )


def install(cfg: ChimeScheduler | None = None) -> None:
    _service(cfg or ChimeScheduler()).install()


def uninstall() -> None:
    _service(ChimeScheduler()).uninstall()
