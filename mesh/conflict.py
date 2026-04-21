"""Priority-table-driven conflict resolver. Deterministic. No LLM.

docs/ARCHITECTURE.md §7:

    route_auth_changes:   [backend, frontend, database]
    schema_changes:       [database, backend, frontend]
    component_changes:    [frontend, backend, database]
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from mesh.dict_store import tokenize_dotpath


# Rule: category -> required subsequence of path tokens.
# A category matches if its rule tokens appear in order within the path;
# wildcards (`*`) match any single segment.
_CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("route_auth_changes", ["routes", "*", "auth_required"]),
    ("schema_changes", ["schema", "*"]),
    ("component_changes", ["components", "*"]),
]


@dataclass(frozen=True)
class Conflict:
    conflict_id: str
    path: str
    parties: list[dict[str, Any]]
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
        self._table = {k: (v or {}).get("winners", []) for k, v in raw.items()}

    def categorize(self, path: str) -> str:
        segs = tokenize_dotpath(path)
        for category, rule in _CATEGORY_RULES:
            if _rule_matches(rule, segs):
                return category
        return "default"

    def detect(
        self,
        path: str,
        incoming_value: Any,
        own_value: Any,
        incoming_agent: str,
        own_agent: str,
        incoming_message_id: str,
        conflict_id: str,
    ) -> Conflict | None:
        if own_value is None or incoming_value == own_value:
            return None
        return Conflict(
            conflict_id=conflict_id,
            path=path,
            parties=[
                {"agent_id": incoming_agent, "value": incoming_value},
                {"agent_id": own_agent, "value": own_value},
            ],
            incoming_message_id=incoming_message_id,
        )

    def resolve(self, conflict: Conflict, resolution_message_id: str) -> Resolution:
        category = self.categorize(conflict.path)
        winners = self._table.get(category) or self._table.get("default") or []
        ids = [p["agent_id"] for p in conflict.parties]

        winner = next((w for w in winners if w in ids), ids[0])
        loser = next((i for i in ids if i != winner), ids[-1])
        reason = (
            f"{category} priority table: " + " > ".join(winners)
            if winners
            else f"fallback (no winners table for {category})"
        )
        return Resolution(
            conflict_id=conflict.conflict_id,
            winner=winner,
            loser=loser,
            reason=reason,
            resolution_message_id=resolution_message_id,
        )


def _rule_matches(rule: list[str], path_segs: list[str]) -> bool:
    """rule must appear as an in-order subsequence of path_segs; `*` matches any."""
    i = 0
    for seg in path_segs:
        if i >= len(rule):
            break
        token = rule[i]
        if token == "*" or token == seg:
            i += 1
    return i == len(rule)
