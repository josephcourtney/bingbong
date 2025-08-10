from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.slow
def test_wav_assets_in_wheel(tmp_path: Path) -> None:
    uv_path = shutil.which("uv")
    if not uv_path:
        pytest.skip("uv not installed; skipping wheel build test")
    subprocess.run([uv_path, "build", "--wheel", "--out-dir", str(tmp_path)], check=True)
    wheel = next(tmp_path.glob("bingbong-*.whl"))
    venv = tmp_path / "venv"
    subprocess.run([uv_path, "venv", str(venv)], check=True)
    python = venv / "bin" / "python"
    subprocess.run([uv_path, "pip", "install", str(wheel), "--python", str(python)], check=True)
    code = (
        "from importlib import resources;"
        "import bingbong.data;"
        "print((resources.files('bingbong.data')/'chime.wav').is_file())"
    )
    out = subprocess.check_output([python, "-c", code])
    assert out.strip() == b"True"
