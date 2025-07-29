from __future__ import annotations

from importlib import import_module
from pathlib import Path

__all__ = ["build", "doctor", "logs", "silence", "status"]

# Import commands so they register with click when module imported
for name in __all__:
    import_module(f"bingbong.commands.{name}")
