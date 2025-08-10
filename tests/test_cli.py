import os
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


def test_status_silence_resume(fs, mocker):
    # Use pyfakefs and set app support via env
    mocker.patch.dict(os.environ, {"BINGBONG_APP_SUPPORT": "/AppSupport"}, clear=False)
    mocker.patch.object(sys, "platform", "darwin")
    runner = CliRunner()
    res = runner.invoke(cli, ["status"])
    assert res.exit_code == 0
    out = res.output
    assert "Label:" in out
    assert "Plist" in out
    res2 = runner.invoke(cli, ["silence", "--minutes", "1"])
    assert res2.exit_code == 0
    assert "[bingbong] Silenced until" in res2.output
    silence_file = "/AppSupport/silence_until.json"
    assert fs.exists(silence_file)
    res3 = runner.invoke(cli, ["resume"])
    assert res3.exit_code == 0
    assert "[bingbong] Silence cleared" in res3.output
    assert not fs.exists(silence_file)


def test_install_platform_guard(mocker):
    runner = CliRunner()
    mocker.patch.object(sys, "platform", "linux")
    res = runner.invoke(cli, ["install", "--chime", __file__, "--pop", __file__])
    assert res.exit_code != 0
    assert "macOS (Darwin) only" in res.output
