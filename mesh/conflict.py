"""Dual-mechanism, deterministic conflict resolver. No LLM.

docs/ARCHITECTURE.md §7 specifies two kinds of conflict:

- Type A (direct path collision): two agents wrote to the same dot-path
  with different values. Resolved via the priority table below.
- Type B (semantic cross-reference): different paths, but a declared rule
  says they must be kept consistent. The demo's hero conflict is Type B
  (`backend.routes.*.auth_required=true` requires a matching
  `frontend.api_calls.*.headers.Authorization`). Rules live in this file
  as frozen dataclasses.

Priority table categories:

    route_auth_changes:   [backend, frontend, database]
    schema_changes:       [database, backend, frontend]
    component_changes:    [frontend, backend, database]
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

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


@dataclass(frozen=True)
class ConflictRule:
    """Type B rule: trigger path on one agent requires a peer path on another.

    `trigger_path_glob` uses `*` for a single segment (segment-aware,
    driven by `tokenize_dotpath`). Each `*` captures a value; the first
    capture is bound to `{route}` in templates for the demo rule.
    `required_peer_path_template` uses `{route}` placeholder.
    """

    id: str
    trigger_agent: str
    trigger_path_glob: str
    trigger_value_predicate: Callable[[Any], bool]
    required_peer_agent: str
    required_peer_path_template: str
    winner: str
    resolution_message: str


@dataclass(frozen=True)
class RuleMatch:
    """One Type B rule firing, after predicate + peer-lookup both pass."""

    rule: ConflictRule
    trigger_path: str
    trigger_value: Any
    captured: dict[str, Any]
    required_peer_path: str
    peer_has_required: bool
    resolution_message: str


RULES: list[ConflictRule] = [
    ConflictRule(
        id="auth_required_on_route",
        trigger_agent="backend",
        trigger_path_glob="routes.*.auth_required",
        trigger_value_predicate=lambda v: v is True,
        required_peer_agent="frontend",
        required_peer_path_template="api_calls.{route}.headers.Authorization",
        winner="backend",
        resolution_message=(
            "Backend route {route} now requires authentication. "
            "Add Authorization header to api_calls.{route}."
        ),
    ),
]


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


def _strip_agent_prefix(path: str, agent_id: str) -> str:
    segs = tokenize_dotpath(path)
    if segs and segs[0] == agent_id:
        segs = segs[1:]
    return ".".join(segs)


def _glob_match(glob: str, path: str) -> list[str] | None:
    """Segment-aware wildcard match. Returns captured segments at each `*`
    position, or None if no match.

    Example: `_glob_match("routes.*.auth_required",
                          "routes./api/users.auth_required")` -> `["/api/users"]`.
    """
    g_segs = tokenize_dotpath(glob)
    p_segs = tokenize_dotpath(path)
    if len(g_segs) != len(p_segs):
        return None
    captured: list[str] = []
    for g, p in zip(g_segs, p_segs):
        if g == "*":
            captured.append(p)
        elif g != p:
            return None
    return captured


def _path_exists(data: dict[str, Any], dotpath: str) -> bool:
    segs = tokenize_dotpath(dotpath)
    cur: Any = data
    for seg in segs:
        if not isinstance(cur, dict) or seg not in cur:
            return False
        cur = cur[seg]
    return cur is not None


def evaluate_rules(
    trigger_agent: str,
    change_path: str,
    change_value: Any,
    peer_dicts: dict[str, dict[str, Any]],
    rules: list[ConflictRule] | None = None,
) -> list[RuleMatch]:
    """Check each Type B rule against a single outgoing change.

    `change_path` is the full agent-qualified path (e.g.
    `backend.routes./api/users.auth_required`). `peer_dicts` maps
    agent_id -> that agent's current dictionary JSON (including its
    own top-level agent_id key). Only rules where `peer_has_required`
    is False are returned — those are the ones that actually fire.
    """
    rules = RULES if rules is None else rules
    out: list[RuleMatch] = []
    for rule in rules:
        if rule.trigger_agent != trigger_agent:
            continue
        scoped_path = _strip_agent_prefix(change_path, trigger_agent)
        captured = _glob_match(rule.trigger_path_glob, scoped_path)
        if captured is None:
            continue
        if not rule.trigger_value_predicate(change_value):
            continue
        # Bind the first capture to `{route}`. Extend here if/when more
        # rules need named captures.
        binding = {"route": captured[0]} if captured else {}
        required_peer_path = rule.required_peer_path_template.format(**binding)
        peer_dict = peer_dicts.get(rule.required_peer_agent, {})
        peer_scope = peer_dict.get(rule.required_peer_agent, {}) \
            if isinstance(peer_dict, dict) else {}
        peer_has = _path_exists(peer_scope, required_peer_path)
        if peer_has:
            continue  # rule condition satisfied -> no conflict
        out.append(
            RuleMatch(
                rule=rule,
                trigger_path=change_path,
                trigger_value=change_value,
                captured=binding,
                required_peer_path=required_peer_path,
                peer_has_required=peer_has,
                resolution_message=rule.resolution_message.format(**binding),
            )
        )
    return out
