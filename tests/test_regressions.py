from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from bingbong.cli import cli


def test_status_output_regression(monkeypatch, file_regression):
    """Snapshot the stable part of `status` output.

    We avoid silence/config-dependent lines to keep it deterministic.
    """
    # Force macOS platform
    import sys as _sys

    monkeypatch.setattr(_sys, "platform", "darwin", raising=True)
    # Stable HOME so the default plist path is deterministic
    monkeypatch.setattr(Path, "home", lambda: Path("/Users/testuser"), raising=True)
    # Provide an app support dir that doesn't exist (so Status shows "Config: (not found)")
    monkeypatch.setenv("BINGBONG_APP_SUPPORT", "/DeterministicAppSupport")
    # Ensure no quiet-hours/env noise
    monkeypatch.delenv("BINGBONG_QUIET_HOURS", raising=False)

    runner = CliRunner()
    res = runner.invoke(cli, ["status"])
    assert res.exit_code == 0
    # Snapshot entire output as text
    file_regression.check(res.output, extension=".txt")
