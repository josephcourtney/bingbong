import subprocess  # noqa: S404
from importlib.resources import files
from pathlib import Path

LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
PLIST_PATH = LAUNCH_AGENTS / "com.josephcourtney.bingbong.plist"


def install() -> None:
    template_path = files("bingbong.data") / "com.josephcourtney.bingbong.plist.in"
    rendered = template_path.read_text(encoding="utf-8")
    PLIST_PATH.write_text(rendered)
    subprocess.run(  # noqa: S603
        ["/bin/launchctl", "load", str(PLIST_PATH)],  # ✅ Full path
        check=True,
    )


def uninstall() -> None:
    subprocess.run(  # noqa: S603
        ["/bin/launchctl", "unload", str(PLIST_PATH)],
        check=True,
    )
    PLIST_PATH.unlink(missing_ok=True)
