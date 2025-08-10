from __future__ import annotations

import time
from typing import TYPE_CHECKING

import click
from rich.text import Text

from bingbong.console import get_console
from bingbong.paths import ensure_outdir

if TYPE_CHECKING:
    from pathlib import Path

    from rich.console import Console


LOG_ROTATE_SIZE = 10 * 1024 * 1024

DEFAULT_LOG_DIR = ensure_outdir()
STDOUT_LOG = DEFAULT_LOG_DIR / "bingbong.out"
STDERR_LOG = DEFAULT_LOG_DIR / "bingbong.err"


def _print_log(log: Path, *, lines: int | None, follow: bool, console: Console) -> None:
    if not log.exists():
        console.print(Text("WARN: No log found.", style="yellow"))
        return

    def read_tail(path: Path, n: int) -> list[str]:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return f.readlines()[-n:]

    def print_lines(lines: list[str]) -> None:
        for line in lines:
            console.print(Text("OK: ", style="green") + line.rstrip())

    if follow:
        console.print(Text(f"Following {log}", style="cyan"))
        with log.open("r", encoding="utf-8", errors="replace") as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    console.print(Text("OK: ", style="green") + line.rstrip())
                else:
                    time.sleep(0.5)
    else:
        all_lines = (
            read_tail(log, lines) if lines else log.read_text(encoding="utf-8", errors="replace").splitlines()
        )
        print_lines(all_lines)


def _rotate(log: Path) -> None:
    if log.exists() and log.stat().st_size > LOG_ROTATE_SIZE:
        backup = log.with_suffix(log.suffix + ".1")
        backup.unlink(missing_ok=True)
        log.rename(backup)


@click.command()
@click.option("--clear", is_flag=True, help="Clear log files instead of displaying them.")
@click.option("--lines", type=int, help="Show only the last N lines of each log.")
@click.option("--follow", is_flag=True, help="Stream appended lines in real-time.")
@click.option("--no-color", is_flag=True, help="Disable color output.")
def logs(*, clear: bool, lines: int | None, follow: bool, no_color: bool) -> None:
    """Display or clear the latest logs for the launchctl job."""
    console = get_console(no_color=no_color)
    for log in [STDOUT_LOG, STDERR_LOG]:
        _rotate(log)
        console.print(f"\n[bold underline]{log}[/]")
        if clear:
            if log.exists():
                log.unlink()
                console.print(Text("OK: Cleared.", style="green"))
            else:
                console.print(Text("WARN: No log to clear.", style="yellow"))
        else:
            _print_log(log, lines=lines, follow=follow, console=console)
