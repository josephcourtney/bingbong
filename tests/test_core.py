from __future__ import annotations

import os
from datetime import timedelta

from bingbong.core import get_silence_until, set_silence_for, silence_active


def test_corrupted_silence_file(fs, mocker):
    mocker.patch.dict(os.environ, {"BINGBONG_APP_SUPPORT": "/AppSupport"}, clear=False)
    fs.create_file("/AppSupport/silence_until.json", contents="{broken")
    assert get_silence_until() is None


def test_silence_active_boundaries(fs, mocker):
    mocker.patch.dict(os.environ, {"BINGBONG_APP_SUPPORT": "/AppSupport"}, clear=False)
    fs.create_dir("/AppSupport")
    until = set_silence_for(1)
    assert silence_active(now=until - timedelta(seconds=1)) is True
    assert silence_active(now=until) is False
