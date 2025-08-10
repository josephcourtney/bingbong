from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "bingbong"
LABEL = "com.bingbong.chimes"  # change if you want a different launchd label


def app_support() -> Path:
    """Return the application support directory (env override-aware)."""
    return Path(
        os.environ.get(
            "BINGBONG_APP_SUPPORT",
            str(Path.home() / "Library" / "Application Support" / APP_NAME),
        )
    )


def config_path() -> Path:
    return app_support() / "config.json"


def silence_path() -> Path:
    return app_support() / "silence_until.json"


class ConfigNotFoundError(FileNotFoundError):
    """Raised when the bingbong configuration file is missing."""


@dataclass
class Config:
    chime_wav: str
    pop_wav: str

    @staticmethod
    def load() -> Config:
        cfg_path = config_path()
        if not cfg_path.exists():
            msg = f"Missing config at {cfg_path}."
            raise ConfigNotFoundError(msg)
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        return Config(chime_wav=data["chime_wav"], pop_wav=data["pop_wav"])

    def save(self) -> None:
        app_dir = app_support()
        app_dir.mkdir(parents=True, exist_ok=True)
        config_path().write_text(
            json.dumps({"chime_wav": self.chime_wav, "pop_wav": self.pop_wav}, indent=2), encoding="utf-8"
        )
