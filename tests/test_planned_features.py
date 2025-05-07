import os
import shutil
import stat
import subprocess
import tomllib
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner
from freezegun import freeze_time
from tomlkit import dumps as tomlkit_dumps

from bingbong import audio, cli, launchctl, notify
from bingbong.paths import DEFAULT_OUTDIR, ensure_outdir
from tests.test_planned_features import isolate_xdg, write_config

CONFIG_PATH = DEFAULT_OUTDIR / "config.toml"


def write_config(cfg: dict) -> None:
    """Write a minimal config.toml under DEFAULT_OUTDIR."""
    from tomlkit import dumps

    DEFAULT_OUTDIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(dumps(cfg))


@pytest.fixture(autouse=True)
def isolate_xdg(monkeypatch, tmp_path):
    """Redirect XDG_DATA_HOME for isolation."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    shutil.rmtree(tmp_path, ignore_errors=True)
    ensure_outdir()
    return tmp_path


def read_config():
    return tomllib.loads(CONFIG_PATH.read_bytes())


#
# 1) Unified cron-driven engine
#


def write_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(tomlkit_dumps(cfg))


def test_arbitrary_cron_expression_translated(isolate_xdg, monkeypatch):
    # e.g. chime every 15 minutes
    cfg = {"chime_schedule": "*/15 * * * *", "suppress_schedule": []}
    write_config(cfg)
    tpl = launchctl.files("bingbong.data") / "com.josephcourtney.bingbong.plist.in"
    monkeypatch.setattr(tpl, "read_text", lambda **kw: "__START_INTERVAL__")
    written = {}
    monkeypatch.setattr(launchctl.PLIST_PATH, "write_text", lambda c, **kw: written.setdefault("c", c))
    launchctl.install()
    content = written["c"]
    # should produce four entries: minute 0,15,30,45
    assert content.count("<dict>") >= 4
    assert "<key>Minute</key><integer>15</integer>" in content
    assert "<key>Minute</key><integer>45</integer>" in content


@pytest.mark.parametrize("bad_cron", ["", "60 * * * *", "bad cron"])
def test_invalid_cron_in_config_errors(bad_cron, isolate_xdg):
    write_config({"chime_schedule": bad_cron, "suppress_schedule": []})
    runner = CliRunner()
    result = runner.invoke(cli.main, ["install"])
    assert result.exit_code != 0
    assert "Invalid cron" in result.output


#
# 2) Interactive configuration wizard
#


def test_wizard_multiple_suppressions_and_options(tmp_path, monkeypatch):
    # Simulate full wizard:
    inputs = (
        "*/30 * * * *\ny\n22:00-23:00\ny\n00:00-06:00\nn\ny\nEurope/London\n/tmp/s1.wav,/tmp/s2.wav" + "\n"
    )
    runner = CliRunner()
    result = runner.invoke(cli.main, ["configure"], input=inputs)
    assert result.exit_code == 0
    cfg = read_config()
    assert cfg["chime_schedule"] == "*/30 * * * *"
    assert cfg["suppress_schedule"] == ["22:00-23:00", "00:00-06:00"]
    assert cfg["respect_dnd"] is True
    assert cfg["timezone"] == "Europe/London"
    assert cfg["custom_sounds"] == ["/tmp/s1.wav", "/tmp/s2.wav"]


def test_wizard_handles_invalid_time_range(tmp_path):
    # if user enters bad range, wizard should reject and reprompt (simulate by EOF)
    runner = CliRunner()
    inputs = "0 * * * *\ny\nbad-range" + "\n"
    result = runner.invoke(cli.main, ["configure"], input=inputs)
    assert result.exit_code != 0
    assert "Invalid time range" in result.output


#
# 3) Enhanced status output
#


@freeze_time("2025-05-07 11:05:00")
def test_status_without_suppression(monkeypatch, isolate_xdg):
    write_config({"chime_schedule": "0 * * * *", "suppress_schedule": []})
    monkeypatch.setenv("HOME", str(isolate_xdg / "home"))
    os.makedirs(isolate_xdg / "home" / "Library" / "LaunchAgents", exist_ok=True)
    # service loaded
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 0, stdout="bingbong", stderr="")
    )
    result = CliRunner().invoke(cli.main, ["status"])
    assert "Next chime: 12:00" in result.output
    assert "Suppressed until" not in result.output


def test_status_shows_manual_pause_remaining(monkeypatch, isolate_xdg):
    write_config({"chime_schedule": "0 * * * *", "suppress_schedule": []})
    pause_until = datetime.now() + timedelta(minutes=10)
    (ensure_outdir() / ".pause_until").write_text(pause_until.isoformat())
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 0, stdout="", stderr="")
    )
    result = CliRunner().invoke(cli.main, ["status"])
    assert "Chimes paused until" in result.output
    assert pause_until.strftime("%H:%M") in result.output


def test_status_missing_or_malformed_config(monkeypatch, isolate_xdg):
    # no config.toml
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()
    result = CliRunner().invoke(cli.main, ["status"])
    assert result.exit_code != 0
    assert "configuration file" in result.output.lower()


#
# 4) Volume control & ducking
#


def test_duck_others_failure_does_not_prevent_chime(monkeypatch, tmp_path, capsys):
    # simulate duck_others raising
    monkeypatch.setattr(audio, "duck_others", lambda: (_ for _ in ()).throw(OSError("coreaudio missing")))
    monkeypatch.setattr(audio, "play_file", lambda _p: print("played"))
    notify.notify_time(outdir=tmp_path)
    out = capsys.readouterr().out
    assert "played" in out
    assert "warning" in out.lower()


#
# 5) Better logging & diagnostics
#


def test_rotation_threshold_constant():
    # ensure module exports a threshold
    assert hasattr(cli, "LOG_ROTATE_SIZE")
    assert isinstance(cli.LOG_ROTATE_SIZE, int)
    assert cli.LOG_ROTATE_SIZE > 0


def test_doctor_prints_log_paths_and_rotated(monkeypatch, isolate_xdg, tmp_path):
    write_config({"chime_schedule": "0 * * * *", "suppress_schedule": []})
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    log_dir = home / "Library" / "Logs"
    os.makedirs(log_dir, exist_ok=True)
    # create current and rotated
    (log_dir / "bingbong.log").write_text("x")
    (log_dir / "bingbong.log.1").write_text("y")
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 0, stdout="bingbong", stderr="")
    )
    result = CliRunner().invoke(cli.main, ["doctor"])
    # doctor should list both files
    assert "bingbong.log" in result.output
    assert "bingbong.log.1" in result.output


def test_log_directory_permission_error(monkeypatch, isolate_xdg):
    write_config({"chime_schedule": "0 * * * *", "suppress_schedule": []})
    home = isolate_xdg / "home"
    monkeypatch.setenv("HOME", str(home))
    log_dir = home / "Library" / "Logs"
    os.makedirs(log_dir, exist_ok=True)
    # remove write permission
    os.chmod(log_dir, stat.S_IREAD)
    result = CliRunner().invoke(cli.main, ["doctor"])
    assert "cannot write logs" in result.output.lower()


#
# 6) Sleep/wake handling
#


@freeze_time("2025-05-07 08:00:00")
def test_on_wake_first_run_creates_state_without_play(monkeypatch, tmp_path):
    out = tmp_path
    # ensure no state file
    state = out / ".last_run"
    if state.exists():
        state.unlink()
    called = []
    monkeypatch.setattr(audio, "play_file", called.append)
    notify.on_wake(outdir=out)
    assert called == []
    assert state.exists()
    assert datetime.fromisoformat(state.read_text()) == datetime(2025, 5, 7, 8, 0, 0)


@freeze_time("2025-05-07 07:05:00")
def test_on_wake_partial_miss_only_next_hour(monkeypatch, tmp_path):
    out = tmp_path
    # last run at 06:37
    (out / ".last_run").write_text("2025-05-07T06:37:00")
    called = []
    monkeypatch.setattr(audio, "play_file", lambda p: called.append(p.name))
    notify.on_wake(outdir=out)
    assert called == ["hour_7.wav"]
    # update state
    new_ts = datetime.fromisoformat((out / ".last_run").read_text())
    assert new_ts == datetime(2025, 5, 7, 7, 5, 0)


def test_on_wake_handles_timezone_boundary(monkeypatch, tmp_path):
    # Simulate DST fallback: last-run before fallback, now after
    # For simplicity, assume code treats timestamps naïvely
    out = tmp_path
    (out / ".last_run").write_text("2025-11-01T01:30:00")
    called = []
    monkeypatch.setattr(audio, "play_file", lambda p: called.append(p.name))
    # pretend now is 01:30 again
    with freeze_time("2025-11-01 01:30:00"):
        notify.on_wake(outdir=out)
    # best effort: should not crash; may record new timestamp
    assert (out / ".last_run").exists()


#
# 7) Documentation & examples
#


def test_readme_cron_snippets_parse_with_croniter():
    from croniter import croniter

    readme = Path(__file__).parent.parent / "README.md"
    text = readme.read_text()
    # find all triple-backtick cron blocks
    for line in text.splitlines():
        if line.strip().startswith("```") or not line.strip():
            continue
        if len(line.split()) == 5 and any(c.isdigit() for c in line):
            assert croniter.is_valid(line.strip()), f"Invalid cron: {line.strip()}"


# 1) suppress_schedule rendering at install time
def test_install_renders_suppress_schedule_crons(isolate_xdg, monkeypatch):
    write_config({
        "chime_schedule": "0 * * * *",
        "suppress_schedule": ["30 1 * * *", "45 2 * * *"],
    })

    tpl = launchctl.files("bingbong.data") / "com.josephcourtney.bingbong.plist.in"
    monkeypatch.setattr(tpl, "read_text", lambda **__: "__TEMPLATE__")

    captured = {}
    monkeypatch.setattr(
        launchctl.PLIST_PATH,
        "write_text",
        lambda content, **__: captured.setdefault("content", content),
    )

    launchctl.install()
    out = captured["content"]

    # Expect at least six <key>Minute</key> (4 default + 2 suppress)
    assert out.count("<key>Minute</key>") >= 6
    assert "<integer>30</integer>" in out
    assert "<integer>45</integer>" in out


def test_configure_invalid_initial_cron(monkeypatch):
    runner = CliRunner()
    result = runner.invoke(cli.main, ["configure"], input="not-a-cron\n")
    assert result.exit_code != 0
    assert "Invalid cron" in result.output


@freeze_time("2025-05-07 22:30:00")
def test_status_reports_scheduled_suppression_window(isolate_xdg, monkeypatch):
    write_config({
        "chime_schedule": "0 * * * *",
        "suppress_schedule": ["22:00-23:00"],
    })

    home = isolate_xdg / "home"
    monkeypatch.setenv("HOME", str(home))
    (home / "Library" / "LaunchAgents").mkdir(parents=True, exist_ok=True)

    # Stub launchctl list -> loaded
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess([], 0, stdout="bingbong", stderr=""),
    )

    result = CliRunner().invoke(cli.main, ["status"])
    assert "Suppressed until 23:00" in result.output


def test_duck_others_success_allows_chime(tmp_path, monkeypatch, capsys):
    outdir = tmp_path
    # ensure at least one chime file exists to avoid rebuild
    (outdir / "silence.wav").write_bytes(b"\0")

    monkeypatch.setattr(audio, "duck_others", lambda: None)
    monkeypatch.setattr(audio, "play_file", lambda p: print("played"))

    notify.notify_time(outdir=outdir)
    out = capsys.readouterr().out
    assert "played" in out


@freeze_time("2025-05-07 10:05:00")
def test_on_wake_multiple_missed_entries(tmp_path, monkeypatch):
    outdir = tmp_path
    # last run at 08:45
    (outdir / ".last_run").write_text("2025-05-07T08:45:00")

    # create only the needed chime files
    for fname in ("hour_9.wav", "quarter_1.wav", "hour_10.wav"):
        (outdir / fname).write_bytes(b"")

    played = []
    monkeypatch.setattr(audio, "play_file", lambda p: played.append(p.name))

    notify.on_wake(outdir=outdir)
    # Should have played at least hour_9 and hour_10
    assert "hour_9.wav" in played
    assert "hour_10.wav" in played

    # Verify state file updated and is timezone-aware
    ts_text = (outdir / ".last_run").read_text()
    ts = datetime.fromisoformat(ts_text)
    assert ts.tzinfo is not None


def test_doctor_rotates_oversize_log(isolate_xdg, monkeypatch):
    home = isolate_xdg / "home"
    monkeypatch.setenv("HOME", str(home))
    log_dir = home / "Library" / "Logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Force a tiny rotate threshold
    import bingbong.cli as _cli

    monkeypatch.setattr(_cli, "LOG_ROTATE_SIZE", 1)

    # Create an oversized log
    big = log_dir / "bingbong.log"
    big.write_bytes(b"xxxxxxxx")

    # Stub launchctl list -> loaded
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess([], 0, stdout="bingbong", stderr=""),
    )

    result = CliRunner().invoke(cli.main, ["doctor"])
    # After doctor, a rotated file should exist
    assert (log_dir / "bingbong.log.1").exists()
    assert "bingbong.log.1" in result.output
