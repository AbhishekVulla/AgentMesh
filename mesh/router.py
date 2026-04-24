"""Dependency-map driven router.

Reads demo/dependency_map.yaml (ARCHITECTURE.md §6) and fans out changes
to subscribing agents via glob-style patterns. `*` matches a single path
segment; `**` matches one or more. The segment-aware matcher uses the
dict_store tokenizer so URL segments like `/api/users` stay intact.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from mesh.dict_store import tokenize_dotpath
from mesh.diff_engine import Change


@dataclass(frozen=True)
class RoutedDiff:
    target: str
    scope: str
    changes: list[Change]
    priority: str  # "low" | "normal" | "high"


class Router:
    def __init__(self, dependency_map_path: Path) -> None:
        self.dependency_map_path = Path(dependency_map_path)
        self._map: dict[str, Any] = {}

    def load(self) -> None:
        with self.dependency_map_path.open("r", encoding="utf-8") as f:
            self._map = yaml.safe_load(f) or {}

    def route(self, from_agent: str, changes: list[Change]) -> list[RoutedDiff]:
        """Fan a diff out to subscribers. Changes matching the same publish
        pattern for the same target+priority are collapsed into a single
        RoutedDiff whose `scope` is the longest common path prefix of the
        grouped changes (segment-aware). The overlay consumes one message
        per subtree, not per leaf."""
        agent_cfg = self._map.get(from_agent, {}) or {}
        publishes: dict[str, Any] = agent_cfg.get("publishes", {}) or {}
        # Group by (target, publish_pattern, priority) first; compute the
        # scope from the group's common prefix once all members are known.
        by_group: dict[tuple[str, str, str], list[Change]] = {}

        for ch in changes:
            relative = _strip_agent_prefix(ch.path, from_agent)
            for pattern, rule in publishes.items():
                if not self._match(pattern, relative):
                    continue
                priority = (rule or {}).get("priority", "normal")
                targets = (rule or {}).get("notify", []) or []
                for target in targets:
                    key = (target, pattern, priority)
                    by_group.setdefault(key, []).append(ch)

        out: list[RoutedDiff] = []
        for (target, _pattern, priority), chs in by_group.items():
            scope = _common_prefix_scope(chs, from_agent)
            out.append(RoutedDiff(target=target, scope=scope, priority=priority, changes=chs))
        return out

    def filter_diff_for(self, target_agent: str, changes: list[Change]) -> list[Change]:
        agent_cfg = self._map.get(target_agent, {}) or {}
        subs: list[str] = agent_cfg.get("subscribes", []) or []
        if not subs:
            return []
        out: list[Change] = []
        for ch in changes:
            if any(self._match(pat, ch.path) for pat in subs):
                out.append(ch)
        return out

    # ------------------------------------------------------------------ glob

    @staticmethod
    def _match(pattern: str, path: str) -> bool:
        pat_segs = tokenize_dotpath(pattern)
        path_segs = tokenize_dotpath(path)
        return _match_segments(pat_segs, path_segs)

    @staticmethod
    def _scope_for(pattern: str, relative_path: str, from_agent: str) -> str:
        """Return the scope string advertised in message.sent.

        MVP: the fully-qualified path of the change (agent-prefixed).
        """
        return f"{from_agent}.{relative_path}" if relative_path else from_agent


def _match_segments(pat: list[str], path: list[str]) -> bool:
    if not pat:
        return not path
    head, *rest = pat
    if head == "**":
        if not rest:
            return len(path) >= 1
        for i in range(1, len(path) + 1):
            if _match_segments(rest, path[i:]):
                return True
        return False
    # Trailing `*` = one-or-more remaining segments (shell-glob convention
    # for routing: `schema.*` means any path under schema.).
    if head == "*" and not rest:
        return len(path) >= 1
    if not path:
        return False
    if head == "*" or head == path[0]:
        return _match_segments(rest, path[1:])
    return False


def _strip_agent_prefix(path: str, agent: str) -> str:
    segs = tokenize_dotpath(path)
    if segs and segs[0] == agent:
        segs = segs[1:]
    return ".".join(segs)


def _common_prefix_scope(changes: list[Change], from_agent: str) -> str:
    """Longest segment-wise common prefix across the grouped changes. For a
    single change, use the change's path minus its leaf."""
    if not changes:
        return from_agent
    all_segs = [tokenize_dotpath(c.path) for c in changes]
    if len(all_segs) == 1:
        segs = all_segs[0]
        # drop the leaf for single-change case, so four `fields.id/name/...`
        # all end up at `backend.models.User.fields` when grouped, but a
        # single leaf change lands at its parent.
        prefix = segs[:-1] if len(segs) > 1 else segs
        return ".".join(prefix)
    shortest = min(len(s) for s in all_segs)
    prefix: list[str] = []
    for i in range(shortest):
        seg = all_segs[0][i]
        if all(s[i] == seg for s in all_segs):
            prefix.append(seg)
        else:
            break
    if not prefix:
        return from_agent
    return ".".join(prefix)
