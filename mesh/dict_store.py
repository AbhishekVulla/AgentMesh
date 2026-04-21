"""Versioned JSON dictionary store with atomic writes and dot-path addressing.

Design notes:
- Atomic write: tempfile.mkstemp + os.replace (Windows 11-safe, ARCHITECTURE.md §9).
- Path tokenizer preserves verbatim segments so route paths containing '/' survive.
- Monotonic version: integer incremented on every successful save().
- History: every save appends a compact record to dictionary.history.jsonl.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DictStore:
    """Owns one agent's dictionary.json on disk."""

    def __init__(self, path: Path, agent_id: str) -> None:
        self.path = Path(path)
        self.agent_id = agent_id
        self._data: dict[str, Any] = {}
        self._version: int = 0

    # ------------------------------------------------------------------ I/O

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            self._data = {
                "_meta": {"agent_id": self.agent_id, "version": 0},
            }
            self._version = 0
            return self._data
        with self.path.open("r", encoding="utf-8") as f:
            self._data = json.load(f)
        meta = self._data.setdefault("_meta", {})
        meta.setdefault("agent_id", self.agent_id)
        self._version = int(meta.get("version", 0))
        return self._data

    def save(self, data: dict[str, Any] | None = None) -> int:
        if data is not None:
            self._data = data
        self._version += 1
        meta = self._data.setdefault("_meta", {})
        meta["agent_id"] = self.agent_id
        meta["version"] = self._version
        meta["updated_at"] = utc_now_iso()
        atomic_write_json(self.path, self._data)
        self._append_history()
        return self._version

    def _append_history(self) -> None:
        hist = self.path.parent / "dictionary.history.jsonl"
        hist.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": utc_now_iso(),
            "agent_id": self.agent_id,
            "version": self._version,
            "snapshot": self._data,
        }
        with hist.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # ----------------------------------------------------------- Dot-paths

    def get(self, dotpath: str) -> Any:
        segments = tokenize_dotpath(dotpath)
        cur: Any = self._data
        for seg in segments:
            if not isinstance(cur, dict) or seg not in cur:
                return None
            cur = cur[seg]
        return cur

    def set(self, dotpath: str, value: Any) -> int:
        segments = tokenize_dotpath(dotpath)
        if not segments:
            raise ValueError("empty dotpath")
        cur: dict[str, Any] = self._data
        for seg in segments[:-1]:
            nxt = cur.get(seg)
            if not isinstance(nxt, dict):
                nxt = {}
                cur[seg] = nxt
            cur = nxt
        cur[segments[-1]] = value
        return self.save()

    # --------------------------------------------------------------- Meta

    @property
    def version(self) -> int:
        return self._version

    @property
    def data(self) -> dict[str, Any]:
        return self._data


# --------------------------------------------------------- Module helpers

def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
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
    """Split on '.' but keep '/'-prefixed segments (URLs/routes) whole.

    `backend.routes./api/users.auth_required`
        -> ['backend', 'routes', '/api/users', 'auth_required']
    """
    if not dotpath:
        return []
    out: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(dotpath):
        ch = dotpath[i]
        if ch == "." and (not buf or not buf[-1].startswith("/") or _route_segment_closed(dotpath, i)):
            if buf:
                out.append("".join(buf))
                buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    if buf:
        out.append("".join(buf))
    # collapse: naive split for most cases; retain `/api/users` style intact.
    return [s for s in out if s]


def _route_segment_closed(s: str, dot_idx: int) -> bool:
    """After a '/'-segment, the dot closes the segment iff what follows is
    NOT another `/` continuation. MVP heuristic: if next char is '/',
    we're still inside the same URL segment."""
    return (dot_idx + 1 >= len(s)) or (s[dot_idx + 1] != "/")


def utc_now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
