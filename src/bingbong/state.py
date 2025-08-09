from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

STATE_FILE = ".state.json"


def _state_path(outdir: Path) -> Path:
    return outdir / STATE_FILE


def load(outdir: Path) -> dict[str, str]:
    """Load state from ``outdir``.

    Returns an empty dictionary if the state file does not exist or is
    malformed.
    """
    path = _state_path(outdir)
    try:
        data: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except OSError:
        return {}
    except json.JSONDecodeError:
        path.unlink(missing_ok=True)
    return {}


def save(outdir: Path, state: dict[str, str]) -> None:
    """Persist ``state`` to ``outdir``."""
    path = _state_path(outdir)
    _ = path.write_text(json.dumps(state), encoding="utf-8")
