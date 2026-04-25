from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[5]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from powcoder_visual import state as _state
except Exception:
    _state = None


def call(method: str, *args: Any, **kwargs: Any) -> None:
    if _state is None:
        return
    try:
        getattr(_state, method)(*args, **kwargs)
    except Exception:
        return
