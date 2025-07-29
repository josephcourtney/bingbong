import shutil
import subprocess  # noqa: S404
import sys
import tomllib
from importlib.resources import files
from pathlib import Path

from .renderer import MinimalRenderer, PlistRenderer
from .scheduler import ChimeScheduler

LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
PLIST_PATH = LAUNCH_AGENTS / "com.josephcourtney.bingbong.plist"


def _load_user_config() -> ChimeScheduler:
    cfgf = Path.home() / ".local" / "share" / "bingbong" / "config.toml"
    scheduler = ChimeScheduler()
    if cfgf.exists():
        cfg = tomllib.loads(cfgf.read_text())
        scheduler = ChimeScheduler(
            chime_schedule=cfg.get("chime_schedule", scheduler.chime_schedule),
            suppress_schedule=cfg.get("suppress_schedule", []),
        )
    return scheduler


def _render_minimal_start_calendar_interval_plist(base, extra, tpl):
    renderer = MinimalRenderer()
    return renderer.render(base, extra, tpl)


def install(*, renderer: PlistRenderer | None = None) -> None:
    template_path = files("bingbong.data") / "com.josephcourtney.bingbong.plist.in"
    tpl = template_path.read_text(encoding="utf-8")

    bin_path = shutil.which("bingbong") or sys.executable
    tpl = tpl.replace("/Users/josephcourtney/.local/bin/bingbong", bin_path)

    scheduler = _load_user_config()

    base = scheduler.minutes_for_chime()
    extra = scheduler.minutes_for_suppression()

    if renderer is None:
        renderer = MinimalRenderer()

    plist = renderer.render(base, extra, tpl)

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
