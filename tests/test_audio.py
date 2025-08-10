from pathlib import Path

import pytest

from bingbong.audio import AFPLAY, play_once, play_repeated


def test_play_once_missing_file(fs):
    missing = Path("/no.wav")  # pyfakefs: path does not exist
    assert not fs.exists(str(missing))
    with pytest.raises(SystemExit):
        play_once(missing)


def test_play_once_nonzero(fake_process, fs):
    f = Path("/a.wav")
    fs.create_file(str(f), contents="0")
    # Expect the player to be invoked and return a non-zero exit code.
    fake_process.register_subprocess(([AFPLAY, str(f)]), returncode=1)
    with pytest.raises(SystemExit):
        play_once(f)


def test_play_repeated_calls(fake_process, fs):
    f = Path("/a.wav")
    fs.create_file(str(f), contents="0")
    # Register three expected successful calls.
    # NOTE: play_once() calls subprocess.run([AFPLAY (Path), str(file)]),
    # so we must register with AFPLAY as a Path to match exactly.
    fake_process.register_subprocess(([AFPLAY, str(f)]), returncode=0, occurrences=3)
    play_repeated(f, 3, delay=0)
    # Ensure exactly three invocations happened.
    # fake_process.calls is a list of arg-lists.
    assert fake_process.call_count([AFPLAY, str(f)]) == 3
