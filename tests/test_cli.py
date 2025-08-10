from pathlib import Path

from click.testing import CliRunner

from bingbong import __version__  # noqa: F401  # simple import sanity check
from bingbong.cli import _default_wavs, cli, compute_pop_count, main


def test_import():
    assert main
    # The CLI group should import and be invokable.
    assert callable(cli)


def test_compute_pop_count_quarters_and_hours():
    # On the hour: chime + N pops
    pops, chime = compute_pop_count(0, 15)  # 3 PM
    assert pops == 3
    assert chime is True
    # Quarter hours
    assert compute_pop_count(15, 10) == (1, False)
    assert compute_pop_count(30, 10) == (2, False)
    assert compute_pop_count(45, 10) == (3, False)
    # Other minutes -> no sound
    assert compute_pop_count(7, 10) == (0, False)


def test_default_wavs_packaged_exist():
    chime, pop = _default_wavs()
    assert Path(chime).is_file()
    assert Path(pop).is_file()


def test_status_and_silence_command(tmp_path, monkeypatch):
    # Redirect app support so we do not touch real user dirs.
    monkeypatch.setenv("BINGBONG_APP_SUPPORT", str(tmp_path / "AppSupport"))
    runner = CliRunner()
    # status should run even with no config present
    res = runner.invoke(cli, ["status"])
    assert res.exit_code == 0
    # silence should create a silence_until.json
    res2 = runner.invoke(cli, ["silence", "--minutes", "1"])
    assert res2.exit_code == 0
    silence_path = tmp_path / "AppSupport" / "silence_until.json"
    assert silence_path.exists()
