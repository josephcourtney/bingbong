import subprocess  # noqa: S404
from datetime import datetime
from pathlib import Path, PosixPath

from croniter import CroniterBadCronError, croniter

DATA_PACKAGE = "bingbong.data"

LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
PLIST_PATH = LAUNCH_AGENTS / "com.josephcourtney.bingbong.plist"
PLIST_LABEL = "com.josephcourtney.bingbong"


# A tiny Path subclass so instance methods can be monkeypatched in tests
class TemplatePath(PosixPath):
    def __new__(cls, *args, **kwargs):
        return PosixPath.__new__(cls, *args, **kwargs)


def files(pkg: str) -> Path:
    # return a Path-subclass instance so tests can setattr read_text
    base = Path(__file__).parent.parent / pkg
    return TemplatePath(str(base))


def _expand_cron(expr: str) -> list[tuple[int, int]]:
    # Only supports minute and hour fields for StartCalendarInterval
    try:
        minute_field, hour_field, *_ = expr.split()
    except ValueError as e:
        msg = f"Invalid cron expression: {expr!r}"
        raise ValueError(msg) from e

    def parse_list(field: str, max_val: int) -> list[int]:
        if field == "*":
            return list(range(max_val + 1))
        if field.startswith("*/"):
            step = int(field[2:])
            return list(range(0, max_val + 1, step))
        parts = field.split(",")
        vals: list[int] = []
        for part in parts:
            if not part.isdigit():
                msg = f"Invalid field {part!r} in cron {expr!r}"
                raise ValueError(msg)
            v = int(part)
            if not (0 <= v <= max_val):
                msg = f"Cron value out of range: {v}"
                raise ValueError(msg)
            vals.append(v)
        return vals

    minutes = parse_list(minute_field, 59)
    hours = parse_list(hour_field, 23)
    return [(h, m) for h in hours for m in minutes]


def _write_plist(path: Path, content: str) -> None:
    """
    Write out the rendered plist.

    Wrapped in a helper so tests can stub it
    without trying to assign to a PosixPath method.
    """
    path.write_text(content, encoding="utf-8")


def install():
    # 1) Try loading user config; if none, skip to writing template unchanged
    from .cli import read_config

    try:
        cfg = read_config()
        chime_cron = cfg.get("chime_schedule")
        if not chime_cron:
            msg = "launchctl.install: no chime_schedule in config"
            raise RuntimeError(msg)
    except FileNotFoundError:
        # No config => render template as-is and load
        tpl = files(DATA_PACKAGE) / "com.josephcourtney.bingbong.plist.in"
        rendered = tpl.read_text(encoding="utf-8")
        LAUNCH_AGENTS.mkdir(parents=True, exist_ok=True)
        _write_plist(PLIST_PATH, rendered)
        subprocess.run(["/bin/launchctl", "load", str(PLIST_PATH)], check=True)  # noqa: S603
        return

    # 2) Validate & expand main chime schedule
    try:
        croniter(chime_cron, datetime.now().astimezone())
    except (ValueError, CroniterBadCronError) as e:
        msg = f"Invalid cron: {chime_cron!r}"
        raise ValueError(msg) from e
    slots = _expand_cron(chime_cron)

    # 3) Validate & expand any suppression schedules
    sup_slots: list[tuple[int, int]] = []
    for expr in cfg.get("suppress_schedule", []):
        try:
            croniter(expr, datetime.now().astimezone())
            sup_slots.extend(_expand_cron(expr))
        except (ValueError, CroniterBadCronError) as e:
            msg = f"Invalid cron: {expr!r}"
            raise ValueError(msg) from e

    # 4) Render StartCalendarInterval entries
    entries = []
    for hour, minute in slots + sup_slots:
        entries.append(
            f"<dict>"
            f"<key>Hour</key><integer>{hour}</integer>"
            f"<key>Minute</key><integer>{minute}</integer>"
            f"</dict>"
        )
    body = "<array>" + "".join(entries) + "</array>"

    # re-fetch the plist template so tests can monkeypatch `files()`
    tpl = files(DATA_PACKAGE) / "com.josephcourtney.bingbong.plist.in"
    template = tpl.read_text(encoding="utf-8")
    rendered = template.replace("__START_INTERVAL__", body)

    LAUNCH_AGENTS.mkdir(parents=True, exist_ok=True)
    _write_plist(PLIST_PATH, rendered)

    subprocess.run(["/bin/launchctl", "load", str(PLIST_PATH)], check=True)  # noqa: S603


def uninstall():
    subprocess.run(["/bin/launchctl", "unload", str(PLIST_PATH)], check=True)  # noqa: S603
    PLIST_PATH.unlink(missing_ok=True)
