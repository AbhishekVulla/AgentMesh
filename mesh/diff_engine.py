"""Path-aware nested-dict diff engine.

Skeleton for Day 2. Produces list[Change] compatible with dict.mutated events
in docs/WEBSOCKET_SCHEMA.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


OpType = Literal["add", "modify", "delete"]


@dataclass(frozen=True)
class Change:
    """Matches the `changes[]` item in dict.mutated."""

    path: str
    op: OpType
    old: Any
    new: Any


def compute_diff(old: dict[str, Any], new: dict[str, Any]) -> list[Change]:
    """Return an ordered list of Changes transforming old → new.

    Order:
      1. Deletes (deepest path first)
      2. Modifies (stable)
      3. Adds (deepest path first)

    The order lets a consumer apply changes sequentially to reproduce `new`.
    Day 2 fills in the body with a recursive walk; full unit tests in
    mesh/tests/test_diff_engine.py cover add / modify / delete / nested.
    """
    raise NotImplementedError("Day 2 — see docs/PLAN.md Day 2 P1 Task 2")
