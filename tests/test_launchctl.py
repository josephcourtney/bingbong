import subprocess

import bingbong.launchctl
from bingbong import launchctl


class DummyFile:
    def __truediv__(self, other):  # noqa: D105
        return self

    def read_text(self, encoding="utf-8"):  # noqa: ARG002, PLR6301
        return "<plist/>"


def test_launchctl_install(monkeypatch, tmp_path):
    dummy_plist = tmp_path / "fake.plist"

    monkeypatch.setattr("bingbong.launchctl.files", lambda _: DummyFile())
    monkeypatch.setattr("bingbong.launchctl.PLIST_PATH", dummy_plist)
    monkeypatch.setattr("pathlib.Path.write_text", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("subprocess.run", lambda *_args, **_kwargs: None)

    monkeypatch.setattr("bingbong.cli.config_path", lambda: tmp_path / "config.toml")
    (tmp_path / "config.toml").write_text('chime_schedule = "0 * * * *"\n')

    bingbong.launchctl.install()


def test_launchctl_uninstall(monkeypatch, tmp_path):
    dummy_plist = tmp_path / "fake.plist"
    dummy_plist.touch()

    monkeypatch.setattr("bingbong.launchctl.PLIST_PATH", dummy_plist)
    monkeypatch.setattr("subprocess.run", lambda *_, **__: None)

    bingbong.launchctl.uninstall()
    assert not dummy_plist.exists()


def test_launchctl_install_creates_dir_and_load(monkeypatch, tmp_path):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    la = home / "Library" / "LaunchAgents"
    plist = la / "com.josephcourtney.bingbong.plist"

    (tmp_path / "config.toml").write_text('chime_schedule = "0 * * * *"\n')

    monkeypatch.setattr("bingbong.launchctl.files", lambda _: DummyFile())
    monkeypatch.setattr("bingbong.launchctl.PLIST_PATH", plist)
    monkeypatch.setattr("bingbong.cli.config_path", lambda: tmp_path / "config.toml")

    calls = []
    monkeypatch.setattr("subprocess.run", lambda args, check: calls.append(args))  # noqa: ARG005

    la.mkdir(parents=True)  # Ensure parent dir exists
    launchctl.install()

    assert plist.exists() or calls  # Either file written or subprocess ran
    assert any("load" in c for c in calls[0])  # sanity check


def test_launchctl_uninstall_removes_and_unloads(monkeypatch, tmp_path):
    home = tmp_path / "home2"
    monkeypatch.setenv("HOME", str(home))
    la = home / "Library" / "LaunchAgents"
    la.mkdir(parents=True, exist_ok=True)
    dummy_plist = la / "com.josephcourtney.bingbong.plist"
    dummy_plist.write_text("x")

    monkeypatch.setattr(launchctl, "PLIST_PATH", dummy_plist)
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda args, check: calls.append(args))  # noqa: ARG005

    launchctl.uninstall()

    assert not dummy_plist.exists()
    assert calls
    assert "unload" in calls[0]
