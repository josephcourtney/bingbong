import plistlib
import subprocess

from bingbong import paths, scheduler, service
from bingbong.service import LABEL, is_loaded


def test_plist_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "ensure_outdir", lambda: tmp_path)

    class DummyLC:
        @staticmethod
        def load(_path):
            return subprocess.CompletedProcess([], 0)

        @staticmethod
        def unload(_path):
            return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr("onginred.service.LaunchctlClient", DummyLC)

    cfg = scheduler.ChimeScheduler()
    svc = service._service(cfg)
    plist_dict = svc.to_plist_dict()
    blob = plistlib.dumps(plist_dict)
    loaded = plistlib.loads(blob)
    assert loaded == plist_dict


def test_is_loaded_via_onginred_client(monkeypatch):
    class DummyClient:
        def list(self):  # noqa: PLR6301
            # mimic dict-like mapping
            return {LABEL: {"PID": 123}}

    monkeypatch.setattr("onginred.service.LaunchctlClient", DummyClient, raising=True)
    # ensure we don't fall back to shell even if present
    monkeypatch.setattr("shutil.which", lambda _cmd: "/bin/launchctl")
    assert is_loaded() is True


def test_is_loaded_fallback_shell(monkeypatch):
    # Make onginred import fail to force fallback
    def boom(*_a, **_k):
        msg = "nope"
        raise ImportError(msg)

    monkeypatch.setattr("onginred.service.LaunchctlClient", boom, raising=False)
    monkeypatch.setattr("shutil.which", lambda _cmd: "/bin/launchctl")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_, **__: subprocess.CompletedProcess([], 0, stdout=f"{LABEL}\n", stderr=""),
    )
    assert is_loaded() is True


def test_is_loaded_no_launchctl(monkeypatch):
    # Neither onginred nor launchctl usable
    def boom(*_a, **_k):
        msg = "nope"
        raise ImportError(msg)

    monkeypatch.setattr("onginred.service.LaunchctlClient", boom, raising=False)
    monkeypatch.setattr("shutil.which", lambda _cmd: None)
    assert is_loaded() is False
