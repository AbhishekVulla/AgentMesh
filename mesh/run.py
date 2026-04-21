"""Session bootstrapper.

Parses config, starts the WebSocket bus + Mini Agents, and runs until
either the demo scenario finishes (mesh.session.ended) or SIGINT.

`python -m mesh.run --config demo/config.yaml` satisfies Gate G3.
"""
from __future__ import annotations

import argparse
import asyncio
import signal
import sys
import uuid
from pathlib import Path
from typing import Any

import yaml

from mesh.conflict import ConflictResolver
from mesh.mini_agent import MiniAgent
from mesh.router import Router
from mesh.ws_server import EventBus


class Session:
    def __init__(self, config: dict[str, Any], config_path: Path) -> None:
        self.config = config
        self.config_path = config_path
        self.session_id = f"sess-{uuid.uuid4().hex[:12]}"

        session_cfg = config.get("session", {}) or {}
        ws_cfg = config.get("websocket", {}) or {}

        self.bus = EventBus(
            session_id=self.session_id,
            port=int(ws_cfg.get("port", 9900)),
            host=ws_cfg.get("host", "localhost"),
            tee_path=Path(ws_cfg.get("tee", ".agentmesh/events/session.jsonl")),
        )

        self.router = Router(Path(session_cfg.get("dependency_map", "demo/dependency_map.yaml")))
        self.resolver = ConflictResolver(
            Path(session_cfg.get("priority_table", "demo/priority_table.yaml"))
        )
        self.router.load()
        self.resolver.load()

        self.agents: list[MiniAgent] = []
        self._agent_cfg: list[dict[str, Any]] = config.get("agents", []) or []
        self._metrics_bytes = 0
        self._metrics_messages = 0
        self._metrics_conflicts = 0
        self._stop = asyncio.Event()

    async def start(self) -> None:
        await self.bus.start()

        loop = asyncio.get_running_loop()
        peer_dirs = {a["id"]: Path(a["agent_dir"]) for a in self._agent_cfg}

        for cfg in self._agent_cfg:
            ma = MiniAgent(
                agent_id=cfg["id"],
                agent_dir=Path(cfg["agent_dir"]),
                router=self.router,
                resolver=self.resolver,
                emit=self._emit_with_metrics,
                loop=loop,
                peers=peer_dirs,
            )
            await ma.start()
            self.agents.append(ma)

        await self.bus.broadcast(
            {
                "event": "mesh.session.started",
                "agents": [
                    {
                        "id": a["id"],
                        "role": a.get("role", a["id"]),
                        "exposes": a.get("exposes", []),
                    }
                    for a in self._agent_cfg
                ],
                "config_path": str(self.config_path),
            }
        )

    async def _emit_with_metrics(self, event: dict[str, Any]) -> None:
        if event.get("event") == "message.sent":
            self._metrics_messages += 1
            self._metrics_bytes += int(event.get("diff_summary", {}).get("bytes", 0))
        elif event.get("event") == "conflict.detected":
            self._metrics_conflicts += 1
        await self.bus.broadcast(event)

    async def emit_tick(self) -> None:
        # Heuristic: savings = 1 - (routed bytes / full-context bytes).
        # Full-context baseline = bytes * N_agents as a cheap proxy.
        n_agents = max(1, len(self._agent_cfg))
        baseline = max(1, self._metrics_bytes * n_agents)
        saved_pct = max(0.0, (1.0 - self._metrics_bytes / baseline) * 100)
        await self.bus.broadcast(
            {
                "event": "metrics.tick",
                "messages_total": self._metrics_messages,
                "conflicts_total": self._metrics_conflicts,
                "bytes_exchanged_total": self._metrics_bytes,
                "estimated_tokens_saved_pct": round(saved_pct, 2),
            }
        )

    async def run_forever(self, duration_s: int = 300) -> None:
        """Drain inputs + emit metrics at 1 Hz, also react to dict.json mtime."""
        mtimes: dict[str, float] = {}
        tick = 0
        try:
            while not self._stop.is_set() and tick < duration_s:
                for ma in self.agents:
                    dj = ma.agent_dir / "dictionary.json"
                    try:
                        m = dj.stat().st_mtime
                    except FileNotFoundError:
                        continue
                    prev = mtimes.get(ma.agent_id, 0.0)
                    if m != prev:
                        mtimes[ma.agent_id] = m
                        if prev != 0.0:
                            await ma.on_dictionary_changed()
                    await ma.drain_input()
                await self.emit_tick()
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass
                tick += 1
        finally:
            await self.end("completed")

    async def end(self, reason: str) -> None:
        await self.bus.broadcast(
            {
                "event": "mesh.session.ended",
                "reason": reason,
                "totals": {
                    "events_emitted": self.bus.seq,
                    "messages_routed": self._metrics_messages,
                    "conflicts": self._metrics_conflicts,
                    "bytes_exchanged": self._metrics_bytes,
                    "duration_ms": 0,
                },
            }
        )
        await self.bus.stop()
        for ma in self.agents:
            await ma.stop()

    def stop(self) -> None:
        self._stop.set()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mesh", description="Start an AgentMesh session.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--duration", type=int, default=120)
    args = parser.parse_args(argv)

    if not args.config.exists():
        print(f"error: config not found: {args.config}", file=sys.stderr)
        return 2
    with args.config.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    session = Session(config, args.config)

    async def _run() -> None:
        await session.start()
        agents_list = [a["id"] for a in session._agent_cfg]
        print(f"[mesh] session {session.session_id} started")
        print(f"[mesh] agents: {agents_list}")
        print(f"[mesh] ws://{session.bus.host}:{session.bus.port}")
        print(f"[mesh] tee: {session.bus.tee_path}")
        await session.run_forever(duration_s=args.duration)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        if hasattr(signal, "SIGINT"):
            loop.add_signal_handler = getattr(loop, "add_signal_handler", None)  # type: ignore
    except NotImplementedError:
        pass  # Windows doesn't support add_signal_handler
    try:
        loop.run_until_complete(_run())
    except KeyboardInterrupt:
        loop.run_until_complete(session.end("aborted"))
    finally:
        loop.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
