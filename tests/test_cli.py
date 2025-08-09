import json
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from click.testing import CliRunner
from freezegun import freeze_time

from bingbong import audio
from bingbong.cli import main


def test_cli_version():
    expected_version = version("bingbong")
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert expected_version in result.output


def test_import():
    assert main


def test_cli_build_and_clean(monkeypatch, tmp_path):
    monkeypatch.setattr("bingbong.paths.ensure_outdir", lambda: tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["build"])
    assert result.exit_code == 0
    assert tmp_path.exists()

    result = runner.invoke(main, ["clean"])
    assert result.exit_code == 0
    assert not any(tmp_path.iterdir())


def test_dry_run_build(monkeypatch, tmp_path):
    monkeypatch.setattr("bingbong.paths.ensure_outdir", lambda: tmp_path)
    called = {"built": False}

    def fake_build(*_args):
        called["built"] = True

    monkeypatch.setattr("bingbong.audio.build_all", fake_build)

    runner = CliRunner()
    result = runner.invoke(main, ["--dry-run", "build"])
    assert result.exit_code == 0
    assert not called["built"]
    assert "DRY RUN" in result.output


def test_cli_install_and_uninstall(monkeypatch):
    captured: dict[str, object] = {}

    from dataclasses import asdict

    def fake_install(cfg):
        captured.update(asdict(cfg))

    monkeypatch.setattr("bingbong.launchctl.install", fake_install)
    monkeypatch.setattr("bingbong.launchctl.uninstall", lambda: None)

    runner = CliRunner()
    result = runner.invoke(main, ["install", "--exit-timeout", "5", "--backoff", "7"])
    assert result.exit_code == 0
    assert captured["exit_timeout"] == 5
    assert captured["throttle_interval"] == 7
    assert captured["crashed"] is True
    assert runner.invoke(main, ["uninstall"]).exit_code == 0


def test_cli_install_handles_existing_file(monkeypatch, tmp_path):
    path = tmp_path / "bingbong.plist"
    calls = {"count": 0}

    def fake_install(_cfg):
        if calls["count"] == 0:
            calls["count"] += 1
            raise FileExistsError(str(path))
        calls["count"] += 1

    removed = {"called": False}

    def fake_unlink(self, missing_ok=False):
        if self == path:
            removed["called"] = True
        else:
            original_unlink(self, missing_ok=missing_ok)

    original_unlink = Path.unlink
    monkeypatch.setattr("bingbong.launchctl.install", fake_install)
    monkeypatch.setattr(Path, "unlink", fake_unlink)

    result = CliRunner().invoke(main, ["install"], input="y\n")
    assert result.exit_code == 0
    assert calls["count"] == 2
    assert removed["called"]
    assert str(path) in result.output


def test_cli_install_retries_on_error(monkeypatch):
    calls = {"count": 0}

    def fake_install(_cfg):
        if calls["count"] == 0:
            calls["count"] += 1
            msg = "boom"
            raise RuntimeError(msg)
        calls["count"] += 1

    monkeypatch.setattr("bingbong.launchctl.install", fake_install)

    result = CliRunner().invoke(main, ["install"], input="y\n")
    assert result.exit_code == 0
    assert calls["count"] == 2
    assert "boom" in result.output


def test_cli_chime(monkeypatch):
    monkeypatch.setattr("bingbong.notify.on_wake", lambda: None)
    monkeypatch.setattr("bingbong.notify.notify_time", lambda: None)
    runner = CliRunner()
    result = runner.invoke(main, ["chime"])
    assert result.exit_code == 0


def test_main_module_runs():
    result = subprocess.run(
        [sys.executable, "-m", "bingbong", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Usage" in result.stdout


def test_cli_clean_when_empty(monkeypatch, tmp_path):
    monkeypatch.setattr("bingbong.paths.ensure_outdir", lambda: tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    result = CliRunner().invoke(main, ["clean"])
    assert "Removed" in result.output


def test_cli_status(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "subprocess.run",
        lambda *_, **__: subprocess.CompletedProcess([], 0, stdout="com.josephcourtney.bingbong", stderr=""),
    )
    monkeypatch.setattr("bingbong.paths.config_path", lambda: tmp_path / "config.toml")
    result = CliRunner().invoke(main, ["status"])
    assert "Service is loaded" in result.output


def test_cli_logs(monkeypatch, tmp_path):
    out = tmp_path / "bingbong.out"
    err = tmp_path / "bingbong.err"
    out.write_text("stdout log")
    err.write_text("stderr log")
    monkeypatch.setattr("bingbong.commands.logs.STDOUT_LOG", out)
    monkeypatch.setattr("bingbong.commands.logs.STDERR_LOG", err)
    result = CliRunner().invoke(main, ["logs"])
    assert "stdout log" in result.output
    assert "stderr log" in result.output


def test_cli_logs_clear(monkeypatch, tmp_path):
    out = tmp_path / "bingbong.out"
    err = tmp_path / "bingbong.err"
    out.write_text("log1")
    err.write_text("log2")
    monkeypatch.setattr("bingbong.commands.logs.STDOUT_LOG", out)
    monkeypatch.setattr("bingbong.commands.logs.STDERR_LOG", err)
    result = CliRunner().invoke(main, ["logs", "--clear"])
    assert "Cleared" in result.output
    assert not out.exists()
    assert not err.exists()


def test_cli_logs_no_file(monkeypatch, tmp_path):
    monkeypatch.setattr("bingbong.commands.logs.STDOUT_LOG", tmp_path / "no.out")
    monkeypatch.setattr("bingbong.commands.logs.STDERR_LOG", tmp_path / "no.err")
    result = CliRunner().invoke(main, ["logs"])
    assert "No log found" in result.output


def test_cli_build_missing_ffmpeg(monkeypatch):
    monkeypatch.setattr("bingbong.ffmpeg.ffmpeg_available", lambda: False)
    result = CliRunner().invoke(main, ["build"])
    assert "ffmpeg is not available" in result.output


def test_main_module_entrypoint():
    result = subprocess.run([sys.executable, "-m", "bingbong"], capture_output=True, text=True, check=False)
    assert "Usage" in result.stdout
    assert result.returncode == 0


def test_cli_build_runtime_error(monkeypatch):
    monkeypatch.setattr("bingbong.ffmpeg.ffmpeg_available", lambda: True)

    def fake_build(*_args):
        msg = "boom"
        raise RuntimeError(msg)

    monkeypatch.setattr("bingbong.audio.build_all", fake_build)

    result = CliRunner().invoke(main, ["build"])
    assert result.exit_code == 0
    assert "boom" in result.output


def test_cli_status_not_loaded(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "subprocess.run", lambda *_, **__: subprocess.CompletedProcess([], 0, stdout="", stderr="")
    )
    monkeypatch.setattr("bingbong.paths.config_path", lambda: tmp_path / "config.toml")
    result = CliRunner().invoke(main, ["status"])
    assert "NOT loaded" in result.output


@freeze_time("2025-05-06 10:00:00")
def test_silence_minutes_creates_file(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setattr("bingbong.paths.ensure_outdir", lambda: tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["silence", "--minutes", "5"])
    assert result.exit_code == 0
    state_file = tmp_path / ".state.json"
    data = json.loads(state_file.read_text())
    assert data["pause_until"].startswith("2025-05-06T10:05:00")


@freeze_time("2025-05-06 22:30:00")
def test_silence_until(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setattr("bingbong.paths.ensure_outdir", lambda: tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["silence", "--until", "2025-05-07 08:00"])
    assert result.exit_code == 0
    state_file = tmp_path / ".state.json"
    data = json.loads(state_file.read_text())
    assert data["pause_until"].startswith("2025-05-07T08:00:00")


def test_silence_mutually_exclusive(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setattr("bingbong.paths.ensure_outdir", lambda: tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["silence", "--minutes", "5", "--until", "2025-05-07 08:00"])
    assert result.exit_code != 0
    assert "Cannot combine --minutes with --until" in result.output


def test_silence_toggle(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setattr("bingbong.paths.ensure_outdir", lambda: tmp_path)

    runner = CliRunner()
    runner.invoke(main, ["silence", "--minutes", "5"])
    state_path = tmp_path / ".state.json"
    assert state_path.exists()

    result = runner.invoke(main, ["silence"])
    assert result.exit_code == 0
    assert "Chimes resumed" in result.output
    data = json.loads(state_path.read_text()) if state_path.exists() else {}
    assert "pause_until" not in data


def test_cli_doctor_success(monkeypatch, tmp_path):
    audio.build_all(tmp_path)
    monkeypatch.setattr("shutil.which", lambda _: "/bin/launchctl")
    monkeypatch.setattr("bingbong.paths.ensure_outdir", lambda: tmp_path)
    monkeypatch.setattr(
        "subprocess.run",
        lambda *_a, **_kw: subprocess.CompletedProcess(
            [], 0, stdout="com.josephcourtney.bingbong", stderr=""
        ),
    )
    monkeypatch.setattr("bingbong.ffmpeg.ffmpeg_available", lambda: True)
    result = CliRunner().invoke(main, ["doctor"])
    assert "All systems go" in result.output


def test_cli_doctor_missing_launchctl(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    result = CliRunner().invoke(main, ["doctor"])
    assert "launchctl' not found" in result.output
    assert result.exit_code == 1


def test_cli_doctor_launchctl_not_loaded(monkeypatch, tmp_path):
    audio.build_all(tmp_path)
    monkeypatch.setattr("bingbong.paths.ensure_outdir", lambda: tmp_path)
    monkeypatch.setattr("shutil.which", lambda _: "/bin/launchctl")
    monkeypatch.setattr(
        "subprocess.run", lambda *_, **__: subprocess.CompletedProcess([], 0, stdout="", stderr="")
    )
    monkeypatch.setattr("bingbong.ffmpeg.ffmpeg_available", lambda: False)

    result = CliRunner().invoke(main, ["doctor"])
    assert "NOT loaded" in result.output


def test_cli_doctor_missing_audio(monkeypatch, tmp_path):
    audio.build_all(tmp_path)
    (tmp_path / "hour_12.wav").unlink()

    monkeypatch.setattr("bingbong.paths.ensure_outdir", lambda: tmp_path)
    monkeypatch.setattr("shutil.which", lambda _: "/bin/launchctl")
    monkeypatch.setattr(
        "subprocess.run",
        lambda *_a, **_kw: subprocess.CompletedProcess(
            [], 0, stdout="com.josephcourtney.bingbong", stderr=""
        ),
    )
    monkeypatch.setattr("bingbong.ffmpeg.ffmpeg_available", lambda: False)

    result = CliRunner().invoke(main, ["doctor"])
    assert "Missing audio files" in result.output
    assert "hour_12.wav" in result.output


def test_cli_doctor_missing_ffmpeg(monkeypatch, tmp_path):
    monkeypatch.setattr("bingbong.paths.ensure_outdir", lambda: tmp_path)
    monkeypatch.setattr("shutil.which", lambda _: "/bin/launchctl")
    monkeypatch.setattr("bingbong.ffmpeg.ffmpeg_available", lambda: False)
    monkeypatch.setattr(
        "subprocess.run",
        lambda *_a, **_kw: subprocess.CompletedProcess(
            [], 0, stdout="com.josephcourtney.bingbong", stderr=""
        ),
    )
    result = CliRunner().invoke(main, ["doctor"])
    assert "FFmpeg cannot be found" in result.output


def test_cli_doctor_failure_exit(monkeypatch, tmp_path):
    monkeypatch.setattr("bingbong.paths.ensure_outdir", lambda: tmp_path)
    monkeypatch.setattr("shutil.which", lambda _: "/bin/launchctl")
    monkeypatch.setattr("bingbong.ffmpeg.ffmpeg_available", lambda: False)
    monkeypatch.setattr(
        "subprocess.run", lambda *_, **__: subprocess.CompletedProcess([], 0, stdout="", stderr="")
    )

    result = CliRunner().invoke(main, ["doctor"])
    assert "Woe! One or more checks failed" in result.output
    assert result.exit_code == 1
