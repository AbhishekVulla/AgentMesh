"""Async WebSocket event bus on :9900.

Broadcasts typed events to every connected client; tees them to
``.agentmesh/events/session.jsonl`` for replay.

Skeleton for Day 2. Day-1 import must succeed so ``python -m mesh.run``
doesn't break.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any


class EventBus:
    def __init__(self, port: int = 9900, tee_path: Path | None = None) -> None:
        self.port = port
        self.tee_path = Path(tee_path) if tee_path else None
        self._clients: set = set()
        self._seq: int = 0

    async def start(self) -> None:
        """Start websockets.serve on self.port. Day 2."""
        raise NotImplementedError("Day 2 — see docs/PLAN.md Day 2 P1 Task 6")

    async def broadcast(self, event: dict[str, Any]) -> None:
        """Send to all clients + append to session.jsonl."""
        raise NotImplementedError("Day 2")

    async def stop(self) -> None:
        raise NotImplementedError("Day 2")
