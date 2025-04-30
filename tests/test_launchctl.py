from pathlib import Path

import bingbong.launchctl


class DummyFile:
    @staticmethod
    def __truediv__(other):  # noqa: D105
        return Path("/dev/null")  # fake path used in test

    @staticmethod
    def read_text(encoding="utf-8"):  # noqa: ARG004
        return "content"


def test_launchctl_install(monkeypatch, tmp_path):
    dummy_plist = tmp_path / "fake.plist"

    monkeypatch.setattr("bingbong.launchctl.files", lambda _: DummyFile())
    monkeypatch.setattr("bingbong.launchctl.PLIST_PATH", dummy_plist)
    monkeypatch.setattr("pathlib.Path.write_text", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("subprocess.run", lambda *_args, **_kwargs: None)

    bingbong.launchctl.install()


def test_launchctl_uninstall(monkeypatch, tmp_path):
    dummy_plist = tmp_path / "fake.plist"
    dummy_plist.touch()

    monkeypatch.setattr("bingbong.launchctl.PLIST_PATH", dummy_plist)
    monkeypatch.setattr("subprocess.run", lambda *_, **__: None)

    bingbong.launchctl.uninstall()
    assert not dummy_plist.exists()
