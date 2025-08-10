from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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


__all__ = [
    "APP_NAME",
    "LABEL",
    "Config",
    "ConfigNotFoundError",
    "app_support",
    "config_path",
    "silence_path",
]


@dataclass(slots=True)
class Config:
    chime_wav: Path
    pop_wav: Path
    version: int = 1

    @staticmethod
    def load() -> Config:
        cfg_path = config_path()
        if not cfg_path.exists():
            msg = f"Missing config at {cfg_path}."
            raise ConfigNotFoundError(msg)
        data: Any = json.loads(cfg_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            msg = f"Invalid config structure in {cfg_path}"
            raise ConfigNotFoundError(msg)
        try:
            chime = Path(data["chime_wav"])
            pop = Path(data["pop_wav"])
        except KeyError as e:  # pragma: no cover - defensive
            msg = f"Missing key in config: {e.args[0]}"
            raise ConfigNotFoundError(msg) from e
        version = int(data.get("version", 1))
        return Config(chime_wav=chime, pop_wav=pop, version=version)

    def save(self) -> None:
        app_dir = app_support()
        app_dir.mkdir(parents=True, exist_ok=True)
        config_path().write_text(
            json.dumps(
                {
                    "chime_wav": str(self.chime_wav),
                    "pop_wav": str(self.pop_wav),
                    "version": self.version,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
