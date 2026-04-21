"""Versioned JSON dictionary store with atomic writes and dot-path addressing.

Skeleton — full implementation lands in Day 2 (see docs/PLAN.md).

Design notes:
- Atomic write: tempfile.mkstemp + os.replace (works on Windows 11, see ARCHITECTURE.md §9).
- Path tokenizer preserves segments verbatim so route paths containing '/' survive.
- Monotonic version: integer incremented on every successful write.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DictStore:
    """Owns one agent's dictionary.json on disk.

    Day-2 will flesh out get/set by dot-path, version bumping, and
    history-append (dictionary.history.jsonl).
    """

    def __init__(self, path: Path, agent_id: str) -> None:
        self.path = Path(path)
        self.agent_id = agent_id
        self._data: dict[str, Any] = {}
        self._version: int = 0

    # ------------------------------------------------------------------ I/O

    def load(self) -> dict[str, Any]:
        """Read JSON from disk; initialize if absent."""
        raise NotImplementedError("Day 2 — see docs/PLAN.md Day 2 P1 Task 1")

    def save(self, data: dict[str, Any]) -> int:
        """Atomic write; returns new version. Uses tempfile + os.replace."""
        raise NotImplementedError("Day 2 — see docs/PLAN.md Day 2 P1 Task 1")

    # ----------------------------------------------------------- Dot-paths

    def get(self, dotpath: str) -> Any:
        """Return value at dot-path, or None if any segment missing."""
        raise NotImplementedError("Day 2")

    def set(self, dotpath: str, value: Any) -> int:
        """Set value at dot-path, bump version, persist atomically."""
        raise NotImplementedError("Day 2")

    # --------------------------------------------------------------- Meta

    @property
    def version(self) -> int:
        return self._version


# --------------------------------------------------------- Module helpers

def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write data to path atomically (tempfile + os.replace).

    The ARCHITECTURE.md §9 reference implementation. Used everywhere that
    JSON lands on disk (dictionary, summary, context, input).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def tokenize_dotpath(dotpath: str) -> list[str]:
    """Split a dot-path while preserving URL/route segments like '/api/users'.

    Rule: a segment starting with '/' extends until the next '.' that is
    followed by a non-slash token. MVP uses a simple rule — if a segment
    starts with '/', consume greedily until the next '.'.

    Day 2 will replace this skeleton with a proper tokenizer + unit tests.
    """
    raise NotImplementedError("Day 2 — see docs/WEBSOCKET_SCHEMA.md path notes")


def utc_now_iso() -> str:
    """ISO-8601 UTC timestamp with millisecond precision, suffix 'Z'."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
