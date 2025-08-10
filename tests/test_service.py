import plistlib
import subprocess

from bingbong import paths, scheduler, service


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
