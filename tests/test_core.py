from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from bingbong.core import get_silence_until, set_silence_for, silence_active

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_corrupted_silence_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BINGBONG_APP_SUPPORT", str(tmp_path))
    path = tmp_path / "silence_until.json"
    path.write_text("{broken", encoding="utf-8")
    assert get_silence_until() is None


def test_silence_active_boundaries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BINGBONG_APP_SUPPORT", str(tmp_path))
    until = set_silence_for(1)
    assert silence_active(now=until - timedelta(seconds=1)) is True
    assert silence_active(now=until) is False
