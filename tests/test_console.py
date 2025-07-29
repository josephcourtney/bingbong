from bingbong.console import err, ok, warn


def test_console_no_color(capsys):
    ok("hi", no_color=True)
    out = capsys.readouterr().out
    assert "\x1b" not in out
    warn("oops", no_color=True)
    out = capsys.readouterr().out
    assert "\x1b" not in out
    err("bad", no_color=True)
    out = capsys.readouterr().out
    assert "\x1b" not in out
