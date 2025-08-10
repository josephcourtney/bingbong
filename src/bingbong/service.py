from __future__ import annotations

from onginred.schedule import LaunchdSchedule
from onginred.service import LaunchdService

from bingbong.config import LABEL
from bingbong.constants import QUARTER_1, QUARTER_2, QUARTER_3


# We build a fixed StartCalendarInterval set for :00/:15/:30/:45 across 24h.
def build_schedule() -> LaunchdSchedule:
    sched = LaunchdSchedule()
    # Every hour at minute 0/15/30/45 (24h)
    for h in range(24):
        for m in (0, QUARTER_1, QUARTER_2, QUARTER_3):
            sched.time.add_calendar_entry(hour=h, minute=m)
    # We don't need KeepAlive; launchd will trigger us at the times above.
    return sched


def service(plist_path: str | None, program_args: list[str]) -> LaunchdService:
    return LaunchdService(
        bundle_identifier=LABEL,
        command=program_args,  # ProgramArguments
        schedule=build_schedule(),
        plist_path=plist_path,  # None -> ~/Library/LaunchAgents/<label>.plist
        # We let logs go to defaults (/var/log/<label>.out/.err)
        launchctl=None,
    )
