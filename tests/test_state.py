import json

from bingbong import state as state_mod
from bingbong.paths import ensure_outdir


def test_state_load_corrupt_json_self_heals(tmp_path, monkeypatch):
    monkeypatch.setattr("bingbong.paths.DEFAULT_OUTDIR", tmp_path)
    outdir = ensure_outdir()
    path = outdir / state_mod.STATE_FILE
    path.write_text("{not:json", encoding="utf-8")

    data = state_mod.load(outdir)
    assert data == {}  # corrupt => reset
    assert not path.exists()  # self-healed (deleted)


def test_state_oversize_resets(tmp_path, monkeypatch):
    monkeypatch.setattr("bingbong.paths.DEFAULT_OUTDIR", tmp_path)
    outdir = ensure_outdir()
    path = outdir / state_mod.STATE_FILE
    # Write > MAX_STATE_BYTES
    path.write_text("x" * (state_mod.MAX_STATE_BYTES + 1), encoding="utf-8")

    data = state_mod.load(outdir)
    assert data == {}
    assert not path.exists()


def test_state_filters_unknown_keys_and_rewrites(tmp_path, monkeypatch):
    monkeypatch.setattr("bingbong.paths.DEFAULT_OUTDIR", tmp_path)
    outdir = ensure_outdir()
    path = outdir / state_mod.STATE_FILE
    bad = {"pause_until": "2025-01-01T00:00:00", "weird": "value"}
    path.write_text(json.dumps(bad), encoding="utf-8")

    data = state_mod.load(outdir)
    assert data == {"pause_until": "2025-01-01T00:00:00"}
    # file is rewritten without the extra key
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved == data


def test_state_load_non_dict(tmp_path, monkeypatch):
    monkeypatch.setattr("bingbong.paths.DEFAULT_OUTDIR", tmp_path)
    outdir = ensure_outdir()
    path = outdir / state_mod.STATE_FILE
    path.write_text("[]", encoding="utf-8")
    data = state_mod.load(outdir)
    assert data == {}
    assert not path.exists()


def test_state_save_atomic(tmp_path, monkeypatch):
    monkeypatch.setattr("bingbong.paths.DEFAULT_OUTDIR", tmp_path)
    outdir = ensure_outdir()
    to_save = {"last_run": "2025-05-06T10:00:00"}
    state_mod.save(outdir, to_save)

    path = outdir / state_mod.STATE_FILE
    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == to_save
