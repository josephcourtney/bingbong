import sys

from click.testing import CliRunner

from bingbong import __version__  # noqa: F401  # simple import sanity check
from bingbong.cli import _default_wavs, cli, compute_pop_count


def test_import():
    assert cli
    # The CLI group should import and be invokable.
    assert callable(cli)


def test_compute_pop_count_quarters_and_hours():
    pops, chime = compute_pop_count(0, 15)
    assert pops == 3
    assert chime is True
    assert compute_pop_count(15, 10) == (1, False)
    assert compute_pop_count(30, 10) == (2, False)
    assert compute_pop_count(45, 10) == (3, False)
    assert compute_pop_count(7, 10) == (0, False)


def test_compute_pop_count_property_hours():
    for h in range(24):
        pops, chime = compute_pop_count(0, h)
        assert pops == (h % 12 or 12)
        assert chime is True


def test_default_wavs_packaged_exist():
    chime, pop = _default_wavs()
    assert chime.is_file()
    assert pop.is_file()


def test_status_silence_resume(tmp_path, monkeypatch):
    monkeypatch.setenv("BINGBONG_APP_SUPPORT", str(tmp_path / "AppSupport"))
    monkeypatch.setattr(sys, "platform", "darwin")
    runner = CliRunner()
    res = runner.invoke(cli, ["status"])
    assert res.exit_code == 0
    res2 = runner.invoke(cli, ["silence", "--minutes", "1"])
    assert res2.exit_code == 0
    silence_file = tmp_path / "AppSupport" / "silence_until.json"
    assert silence_file.exists()
    res3 = runner.invoke(cli, ["resume"])
    assert res3.exit_code == 0
    assert not silence_file.exists()


def test_install_platform_guard(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(sys, "platform", "linux")
    res = runner.invoke(cli, ["install", "--chime", __file__, "--pop", __file__])
    assert res.exit_code != 0
