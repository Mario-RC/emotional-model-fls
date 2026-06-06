"""Compatibility entrypoint for running the emotional model from the repo root."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

_EXPORTED_NAMES = {"EmotionalModel", "shared_data"}
__all__ = sorted(_EXPORTED_NAMES)


def __getattr__(name: str):
    if name in _EXPORTED_NAMES:
        from emotional_model_fls.runtime import EmotionalModel, shared_data

        return {"EmotionalModel": EmotionalModel, "shared_data": shared_data}[name]
    raise AttributeError(name)


if __name__ == "__main__":
    from emotional_model_fls.cli import main

    raise SystemExit(main())
