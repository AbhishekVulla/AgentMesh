"""Priority-table-driven conflict resolver. Deterministic. No LLM.

docs/ARCHITECTURE.md §7 defines the categories and winners:

    route_auth_changes:   [backend, frontend, database]   # backend wins
    schema_changes:       [database, backend, frontend]   # database wins
    component_changes:    [frontend, backend, database]   # frontend wins

Skeleton for Day 2.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Conflict:
    conflict_id: str
    path: str
    parties: list[dict[str, Any]]  # [{agent_id, value}, {agent_id, value}]
    incoming_message_id: str


@dataclass(frozen=True)
class Resolution:
    conflict_id: str
    winner: str
    loser: str
    reason: str
    resolution_message_id: str


class ConflictResolver:
    """Lookup-table resolver. No dynamic dispatch, no LLM, no network."""

    def __init__(self, priority_table_path: Path) -> None:
        self.priority_table_path = Path(priority_table_path)
        self._table: dict[str, list[str]] = {}

    def load(self) -> None:
        with self.priority_table_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        # MVP: map each category to its ordered winners list.
        self._table = {k: v.get("winners", []) for k, v in raw.items()}

    def categorize(self, path: str) -> str:
        """Map a dot-path to a priority category. Day 2."""
        raise NotImplementedError("Day 2")

    def detect(
        self, incoming_scope: str, incoming_value: Any, own_value: Any
    ) -> Conflict | None:
        """Return a Conflict if values disagree, else None."""
        raise NotImplementedError("Day 2")

    def resolve(self, conflict: Conflict) -> Resolution:
        """Pick a winner by priority table. Deterministic."""
        raise NotImplementedError("Day 2 — see docs/PLAN.md Day 2 P1 Task 4")
