"""Path-aware nested-dict diff engine.

Produces ordered list[Change] compatible with `dict.mutated` events
per docs/WEBSOCKET_SCHEMA.md §4.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Literal


OpType = Literal["add", "modify", "delete"]


@dataclass(frozen=True)
class Change:
    path: str
    op: OpType
    old: Any
    new: Any

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_diff(old: dict[str, Any], new: dict[str, Any]) -> list[Change]:
    """Return an ordered list of Changes transforming old -> new.

    Order:
      1. Deletes (deepest first)
      2. Modifies (stable insertion order)
      3. Adds (shallowest first)

    Top-level key `_meta` is ignored (it's bookkeeping, not domain data).
    Lists and scalars are treated as leaves — a list change is a single
    `modify` on the list path, not an element-wise diff.
    """
    deletes: list[Change] = []
    modifies: list[Change] = []
    adds: list[Change] = []

    old_clean = {k: v for k, v in (old or {}).items() if k != "_meta"}
    new_clean = {k: v for k, v in (new or {}).items() if k != "_meta"}
    _walk("", old_clean, new_clean, deletes, modifies, adds)

    deletes.sort(key=lambda c: c.path.count("."), reverse=True)
    adds.sort(key=lambda c: c.path.count("."))
    return deletes + modifies + adds


def _walk(
    prefix: str,
    old: Any,
    new: Any,
    deletes: list[Change],
    modifies: list[Change],
    adds: list[Change],
) -> None:
    if isinstance(old, dict) and isinstance(new, dict):
        old_keys = set(old.keys())
        new_keys = set(new.keys())
        for k in old_keys - new_keys:
            _emit_tree(_join(prefix, k), old[k], "delete", deletes)
        for k in new_keys - old_keys:
            _emit_tree(_join(prefix, k), new[k], "add", adds)
        for k in old_keys & new_keys:
            _walk(_join(prefix, k), old[k], new[k], deletes, modifies, adds)
        return
    if old != new:
        modifies.append(Change(prefix, "modify", old, new))


def _emit_tree(path: str, value: Any, op: OpType, out: list[Change]) -> None:
    """For a whole added/deleted subtree, emit one Change per leaf so the
    router can match fine-grained patterns like `schema.*` or `routes.**`."""
    if isinstance(value, dict) and value:
        for k, v in value.items():
            _emit_tree(_join(path, k), v, op, out)
        return
    if op == "add":
        out.append(Change(path, "add", None, value))
    else:
        out.append(Change(path, "delete", value, None))


def _join(prefix: str, key: str) -> str:
    return key if not prefix else f"{prefix}.{key}"
