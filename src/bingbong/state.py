from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from .utils import atomic_write_text

if TYPE_CHECKING:
    from pathlib import Path

STATE_FILE = ".state.json"
MAX_STATE_BYTES = 64 * 1024  # cap to avoid reading pathological files
ALLOWED_KEYS = {"pause_until", "last_run"}
logger = logging.getLogger("bingbong.state")


def _state_path(outdir: Path) -> Path:
    return outdir / STATE_FILE


def load(outdir: Path) -> dict[str, str]:
    """Load state from ``outdir``.

    Returns an empty dictionary if the state file does not exist or is
    malformed.
    """
    path = _state_path(outdir)
    # quick existence & size checks
    try:
        st = path.stat()
    except OSError:
        return {}
    if st.st_size > MAX_STATE_BYTES:
        logger.warning("state file too large (%d bytes); resetting", st.st_size)
        path.unlink(missing_ok=True)
        return {}

    # read & parse
    try:
        raw = path.read_text(encoding="utf-8", errors="strict")
    except OSError:
        return {}
    try:
        data: object = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("state file corrupt JSON; resetting")
        path.unlink(missing_ok=True)
        return {}

    if not isinstance(data, dict):
        logger.warning("state file not a dict; resetting")
        path.unlink(missing_ok=True)
        return {}

    # normalize and filter unexpected keys/types
    cleaned: dict[str, str] = {}
    for k, v in data.items():
        if str(k) in ALLOWED_KEYS:
            cleaned[str(k)] = str(v)
        else:
            logger.debug("dropping unknown state key: %r", k)

    # self-heal if we changed anything
    if cleaned != data:
        try:
            atomic_write_text(path, json.dumps(cleaned))
        except OSError as e:
            logger.debug("unable to rewrite cleaned state: %s", e)

    return cleaned


def save(outdir: Path, state: dict[str, str]) -> None:
    """Persist ``state`` to ``outdir``."""
    path = _state_path(outdir)
    try:
        atomic_write_text(path, json.dumps({str(k): str(v) for k, v in state.items()}))
    except OSError:
        logger.exception("Failed to write state file")
