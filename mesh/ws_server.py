"""Async WebSocket event bus on :9900.

Broadcasts typed events (validated against pydantic schema) to every
connected client; tees them to `.agentmesh/events/session.jsonl`.

The hot path has no LLM calls. Every event is:
  1. Stamped with seq + ts + session_id
  2. Validated via EventAdapter (pydantic discriminated union)
  3. Fanned out to all ws clients (best effort, dead sockets dropped)
  4. Appended as a single JSON line to session.jsonl (atomic append)
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import websockets
from websockets.server import WebSocketServerProtocol

from mesh.dict_store import utc_now_iso
from mesh.schemas.events import EventAdapter


class EventBus:
    def __init__(
        self,
        session_id: str,
        port: int = 9900,
        host: str = "localhost",
        tee_path: Path | None = None,
    ) -> None:
        self.session_id = session_id
        self.port = port
        self.host = host
        self.tee_path = Path(tee_path) if tee_path else None
        self._clients: set[WebSocketServerProtocol] = set()
        self._seq: int = 0
        self._server = None
        self._lock = asyncio.Lock()
        if self.tee_path:
            self.tee_path.parent.mkdir(parents=True, exist_ok=True)
            self.tee_path.write_text("", encoding="utf-8")

    async def start(self) -> None:
        self._server = await websockets.serve(self._handler, self.host, self.port)

    async def _handler(self, ws: WebSocketServerProtocol) -> None:
        self._clients.add(ws)
        try:
            async for _ in ws:
                pass
        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.discard(ws)

    async def broadcast(self, event: dict[str, Any]) -> None:
        async with self._lock:
            event = dict(event)
            event.setdefault("seq", self._seq)
            event.setdefault("ts", utc_now_iso())
            event.setdefault("session_id", self.session_id)
            self._seq += 1

            # Validate — pydantic catches schema drift before it ships.
            validated = EventAdapter.validate_python(event)
            payload = validated.model_dump(mode="json", by_alias=True)
            line = json.dumps(payload, ensure_ascii=False)

            if self.tee_path:
                with self.tee_path.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")

            dead: list[WebSocketServerProtocol] = []
            for ws in list(self._clients):
                try:
                    await ws.send(line)
                except (websockets.ConnectionClosed, RuntimeError):
                    dead.append(ws)
            for ws in dead:
                self._clients.discard(ws)

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    @property
    def seq(self) -> int:
        return self._seq

    @property
    def client_count(self) -> int:
        return len(self._clients)
