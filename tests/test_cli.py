import subprocess
import sys

from click.testing import CliRunner

from bingbong import audio
from bingbong.cli import main


def test_import():
    assert main


def test_cli_build_and_clean(monkeypatch, tmp_path):
    # Patch ensure_outdir to point to temp dir
    monkeypatch.setattr("bingbong.cli.ensure_outdir", lambda: tmp_path)

    runner = CliRunner()

    result = runner.invoke(main, ["build"])
    assert result.exit_code == 0
    assert tmp_path.exists()

    result = runner.invoke(main, ["clean"])
    assert result.exit_code == 0
    assert not tmp_path.exists()


def test_cli_install_and_uninstall(monkeypatch):
    monkeypatch.setattr("bingbong.launchctl.install", lambda: None)
    monkeypatch.setattr("bingbong.launchctl.uninstall", lambda: None)

    runner = CliRunner()
    assert runner.invoke(main, ["install"]).exit_code == 0
    assert runner.invoke(main, ["uninstall"]).exit_code == 0


def test_cli_chime(monkeypatch):
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
    # Ensure DEFAULT_OUTDIR does not exist
    if tmp_path.exists():
        for child in tmp_path.iterdir():
            child.unlink()
        tmp_path.rmdir()
    monkeypatch.setattr("bingbong.cli.ensure_outdir", lambda: tmp_path)
    result = CliRunner().invoke(main, ["clean"])
    assert "No generated files found." in result.output


def test_cli_status(monkeypatch):
    monkeypatch.setattr(
        "subprocess.run",
        lambda *_, **__: subprocess.CompletedProcess([], 0, stdout="com.josephcourtney.bingbong", stderr=""),
    )
    result = CliRunner().invoke(main, ["status"])
    assert "Service is loaded" in result.output


def test_cli_logs(tmp_path, monkeypatch):
    out = tmp_path / "bingbong.out"
    err = tmp_path / "bingbong.err"
    out.write_text("stdout log")
    err.write_text("stderr log")
    monkeypatch.setattr("bingbong.cli.STDOUT_LOG", out)
    monkeypatch.setattr("bingbong.cli.STDERR_LOG", err)
    result = CliRunner().invoke(main, ["logs"])
    assert "stdout log" in result.output
    assert "stderr log" in result.output


def test_cli_build_missing_ffmpeg(monkeypatch):
    monkeypatch.setattr("bingbong.cli.ffmpeg_available", lambda: False)
    monkeypatch.setattr("bingbong.audio.build_all", lambda: None)
    result = CliRunner().invoke(main, ["build"])
    assert "ffmpeg is not available" in result.output


def test_main_module_entrypoint():
    result = subprocess.run([sys.executable, "-m", "bingbong"], capture_output=True, text=True, check=False)
    assert "Usage" in result.stdout
    assert result.returncode == 0


def test_cli_build_runtime_error(monkeypatch):
    monkeypatch.setattr("bingbong.cli.ffmpeg_available", lambda: True)
    monkeypatch.setattr("bingbong.audio.build_all", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    result = CliRunner().invoke(main, ["build"])
    assert "boom" in result.output


def test_cli_status_not_loaded(monkeypatch):
    monkeypatch.setattr(
        "subprocess.run", lambda *_, **__: subprocess.CompletedProcess([], 0, stdout="", stderr="")
    )
    result = CliRunner().invoke(main, ["status"])
    assert "NOT loaded" in result.output


def test_cli_logs_clear(monkeypatch, tmp_path):
    out = tmp_path / "bingbong.out"
    err = tmp_path / "bingbong.err"
    out.write_text("log1")
    err.write_text("log2")

    monkeypatch.setattr("bingbong.cli.STDOUT_LOG", out)
    monkeypatch.setattr("bingbong.cli.STDERR_LOG", err)

    result = CliRunner().invoke(main, ["logs", "--clear"])
    assert "Cleared" in result.output
    assert not out.exists()
    assert not err.exists()


def test_cli_logs_no_file(monkeypatch, tmp_path):
    monkeypatch.setattr("bingbong.cli.STDOUT_LOG", tmp_path / "no.out")
    monkeypatch.setattr("bingbong.cli.STDERR_LOG", tmp_path / "no.err")

    result = CliRunner().invoke(main, ["logs"])
    assert "No log found" in result.output


def test_cli_doctor_success(monkeypatch, tmp_path):
    audio.build_all(tmp_path)

    monkeypatch.setattr("shutil.which", lambda _: "/bin/launchctl")
    monkeypatch.setattr(
        "subprocess.run",
        lambda *_a, **_kw: subprocess.CompletedProcess(
            [], 0, stdout="com.josephcourtney.bingbong", stderr=""
        ),
    )
    monkeypatch.setattr("bingbong.cli.ensure_outdir", lambda: tmp_path)
    monkeypatch.setattr("bingbong.cli.ffmpeg_available", lambda: True)

    result = CliRunner().invoke(main, ["doctor"])
    assert "All systems go" in result.output


def test_cli_doctor_missing_launchctl(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    result = CliRunner().invoke(main, ["doctor"])
    assert "launchctl' not found" in result.output
    assert result.exit_code == 1


def test_cli_doctor_launchctl_not_loaded(monkeypatch, tmp_path):
    audio.build_all(tmp_path)

    monkeypatch.setattr("shutil.which", lambda _: "/bin/launchctl")
    monkeypatch.setattr(
        "subprocess.run", lambda *_, **__: subprocess.CompletedProcess([], 0, stdout="", stderr="")
    )
    monkeypatch.setattr("bingbong.cli.ensure_outdir", lambda: tmp_path)
    monkeypatch.setattr("bingbong.cli.ffmpeg_available", lambda: True)

    result = CliRunner().invoke(main, ["doctor"])
    assert "NOT loaded" in result.output


def test_cli_doctor_missing_audio(monkeypatch, tmp_path):
    audio.build_all(tmp_path)
    (tmp_path / "hour_12.wav").unlink()  # simulate missing

    monkeypatch.setattr("shutil.which", lambda _: "/bin/launchctl")
    monkeypatch.setattr(
        "subprocess.run",
        lambda *_, **__: subprocess.CompletedProcess([], 0, stdout="com.josephcourtney.bingbong", stderr=""),
    )
    monkeypatch.setattr("bingbong.cli.ensure_outdir", lambda: tmp_path)
    monkeypatch.setattr("bingbong.cli.ffmpeg_available", lambda: True)

    result = CliRunner().invoke(main, ["doctor"])
    assert "Missing audio files" in result.output
    assert "hour_12.wav" in result.output


def test_cli_doctor_missing_ffmpeg(monkeypatch, tmp_path):
    audio.build_all(tmp_path)

    monkeypatch.setattr("shutil.which", lambda _: "/bin/launchctl")
    monkeypatch.setattr(
        "subprocess.run",
        lambda *_, **__: subprocess.CompletedProcess([], 0, stdout="com.josephcourtney.bingbong", stderr=""),
    )
    monkeypatch.setattr("bingbong.cli.ensure_outdir", lambda: tmp_path)
    monkeypatch.setattr("bingbong.cli.ffmpeg_available", lambda: False)

    result = CliRunner().invoke(main, ["doctor"])
    assert "FFmpeg cannot be found" in result.output


def test_cli_doctor_failure_exit(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda _: "/bin/launchctl")
    monkeypatch.setattr("bingbong.cli.ffmpeg_available", lambda: False)
    monkeypatch.setattr(
        "subprocess.run", lambda *_, **__: subprocess.CompletedProcess([], 0, stdout="", stderr="")
    )
    monkeypatch.setattr("bingbong.cli.ensure_outdir", lambda: tmp_path)

    result = CliRunner().invoke(main, ["doctor"])
    assert "Woe! One or more checks failed" in result.output
    assert result.exit_code == 1
