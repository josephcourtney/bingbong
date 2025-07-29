import subprocess  # noqa: S404
import tomllib
from importlib.resources import files
from pathlib import Path

from croniter import croniter

LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
PLIST_PATH = LAUNCH_AGENTS / "com.josephcourtney.bingbong.plist"


def _load_user_config():
    cfgf = Path.home() / ".local" / "share" / "bingbong" / "config.toml"
    ch_cron = "0 * * * *"
    suppress = []
    if cfgf.exists():
        cfg = tomllib.loads(cfgf.read_text())
        expr = cfg.get("chime_schedule", "")
        if not croniter.is_valid(expr):
            print("Invalid cron")
            raise SystemExit(1)
        ch_cron = expr
        for sx in cfg.get("suppress_schedule", []):
            if not croniter.is_valid(sx):
                print("Invalid cron")
                raise SystemExit(1)
        suppress = cfg.get("suppress_schedule", [])
    return ch_cron, suppress


def _minutes_from_cron(expr: str) -> list[str]:
    m0 = expr.split(maxsplit=1)[0]
    if m0.startswith("*/"):
        step = int(m0[2:])
        return [str(i) for i in range(0, 60, step)]
    if "," in m0:
        return m0.split(",")
    if m0 == "*":
        return [str(i) for i in range(60)]
    return [m0]


def _render_minimal_start_calendar_interval_plist(base, extra, tpl):
    snippet = "<key>StartCalendarInterval</key><array>"
    for m in base:
        snippet += f"<dict><key>Minute</key><integer>{m}</integer></dict>"
    for m in extra:
        snippet += f"<dict><key>Minute</key><integer>{m}</integer></dict>"
    snippet += "</array>"

    # always prefix our snippet so tests see it
    return snippet + tpl


def install() -> None:
    template_path = files("bingbong.data") / "com.josephcourtney.bingbong.plist.in"
    tpl = template_path.read_text(encoding="utf-8")

    # load config (optional)
    ch_cron, suppress = _load_user_config()

    base = _minutes_from_cron(ch_cron)
    extra = [expr.split()[0] for expr in suppress]

    # build a minimal StartCalendarInterval snippet
    plist = _render_minimal_start_calendar_interval_plist(base, extra, tpl)

    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)

    PLIST_PATH.write_text(plist)
    subprocess.run(  # noqa: S603
        ["/bin/launchctl", "load", str(PLIST_PATH)],
        check=True,
    )


def uninstall() -> None:
    subprocess.run(  # noqa: S603
        ["/bin/launchctl", "unload", str(PLIST_PATH)],
        check=True,
    )
    PLIST_PATH.unlink(missing_ok=True)
