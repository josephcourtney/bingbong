from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def test_wav_assets_in_wheel(tmp_path: Path) -> None:
    uv_path = shutil.which("uv")
    assert uv_path
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
