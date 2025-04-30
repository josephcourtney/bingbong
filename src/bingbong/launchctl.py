import subprocess
from importlib.resources import files
from pathlib import Path

LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
PLIST_PATH = LAUNCH_AGENTS / "com.josephcourtney.bingbong.plist"


def install():
    template_path = files("bingbong.data") / "com.josephcourtney.bingbong.plist.in"
    rendered = template_path.read_text(encoding="utf-8")
    PLIST_PATH.write_text(rendered)
    subprocess.run(["launchctl", "load", str(PLIST_PATH)], check=True)


def uninstall():
    subprocess.run(["launchctl", "unload", str(PLIST_PATH)], check=True)
    PLIST_PATH.unlink(missing_ok=True)
