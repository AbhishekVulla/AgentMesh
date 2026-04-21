"""Mini Agent sidecar: watches one major agent's directory, diffs, routes, resolves.

Skeleton for Day 2. Wires together watchdog + dict_store + diff_engine +
router + conflict. Emits WebSocket events at every decision point.
"""
from __future__ import annotations

from pathlib import Path

from mesh.conflict import ConflictResolver
from mesh.dict_store import DictStore
from mesh.router import Router


class MiniAgent:
    def __init__(
        self,
        agent_id: str,
        agent_dir: Path,
        router: Router,
        resolver: ConflictResolver,
        emit,  # callable taking an event dict
    ) -> None:
        self.agent_id = agent_id
        self.agent_dir = Path(agent_dir)
        self.store = DictStore(self.agent_dir / "dictionary.json", agent_id=agent_id)
        self.router = router
        self.resolver = resolver
        self.emit = emit

    def start(self) -> None:
        """Install file watcher, drain input.json, begin event loop."""
        raise NotImplementedError("Day 2 — see docs/PLAN.md Day 2 P1 Task 5")

    def stop(self) -> None:
        raise NotImplementedError("Day 2")
