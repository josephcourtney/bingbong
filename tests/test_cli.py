import subprocess
import sys

from click.testing import CliRunner

from bingbong.cli import main
from bingbong.paths import DEFAULT_OUTDIR


def test_import():
    assert main


def test_cli_build_and_clean():
    runner = CliRunner()

    result = runner.invoke(main, ["build"])
    assert result.exit_code == 0
    assert DEFAULT_OUTDIR.exists()

    result = runner.invoke(main, ["clean"])
    assert result.exit_code == 0
    assert not DEFAULT_OUTDIR.exists()


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

    monkeypatch.setattr("bingbong.cli.DEFAULT_OUTDIR", tmp_path)
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
