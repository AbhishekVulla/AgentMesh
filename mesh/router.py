"""Dependency-map driven router.

Reads demo/dependency_map.yaml (ARCHITECTURE.md §6) and, given an agent's
diff, returns the list of (target_agent, diff_subset) to fan out to.

Skeleton for Day 2. Uses glob-style patterns: ``routes.*``,
``backend.routes./api/users.auth_required``, etc.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

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
        """Parse YAML into publish/subscribe indices."""
        with self.dependency_map_path.open("r", encoding="utf-8") as f:
            self._map = yaml.safe_load(f) or {}

    def route(self, from_agent: str, changes: list[Change]) -> list[RoutedDiff]:
        """Fan out changes to subscribing agents per the dependency map.

        Day 2 implements glob-matching. MVP patterns:
          - ``routes.*`` — any path under routes
          - ``models.*``
          - ``schema.*``
        """
        raise NotImplementedError("Day 2 — see docs/PLAN.md Day 2 P1 Task 3")

    def filter_diff_for(self, target_agent: str, changes: list[Change]) -> list[Change]:
        """Return only the subset of changes the target cares about."""
        raise NotImplementedError("Day 2")
