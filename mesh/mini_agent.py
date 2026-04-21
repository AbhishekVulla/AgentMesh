"""Mini Agent sidecar: watches one major agent's directory, diffs, routes.

The hot path has no LLM calls. On dictionary.json mutation:
  1. Load the new snapshot
  2. compute_diff vs the last-known snapshot
  3. Emit `dict.mutated` via the event bus
  4. Router.route -> emit `message.sent` per routed target
  5. Write each routed diff into the target's input.json (atomic)

On input.json arrival at this agent:
  1. Emit `message.delivered`
  2. For each change, detect conflicts against local state
  3. Emit `conflict.detected` then `conflict.resolved` (deterministic)
"""
from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable

from mesh.conflict import ConflictResolver, RuleMatch, evaluate_rules
from mesh.dict_store import DictStore, atomic_write_json, tokenize_dotpath
from mesh.diff_engine import Change, compute_diff
from mesh.router import RoutedDiff, Router

Emit = Callable[[dict[str, Any]], Awaitable[None]]


class MiniAgent:
    def __init__(
        self,
        agent_id: str,
        agent_dir: Path,
        router: Router,
        resolver: ConflictResolver,
        emit: Emit,
        loop: asyncio.AbstractEventLoop,
        peers: dict[str, Path],
    ) -> None:
        self.agent_id = agent_id
        self.agent_dir = Path(agent_dir)
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        self.store = DictStore(self.agent_dir / "dictionary.json", agent_id=agent_id)
        self.router = router
        self.resolver = resolver
        self.emit = emit
        self.loop = loop
        self.peers = peers  # peer_id -> peer agent_dir
        self._last_snapshot: dict[str, Any] = {}

        self._input_path = self.agent_dir / "input.json"
        self._last_input_seen: int = 0

    # --------------------------------------------------- init / teardown

    async def start(self) -> None:
        self.store.load()
        self._last_snapshot = _strip_meta(self.store.data)
        # Initialize input.json as empty queue
        if not self._input_path.exists():
            atomic_write_json(self._input_path, {"queue": []})

    async def stop(self) -> None:
        return None

    # ---------------------------------------------- dictionary -> outgoing

    async def on_dictionary_changed(self) -> None:
        """Called by the session loop after an agent writes dictionary.json."""
        self.store.load()
        new_snapshot = _strip_meta(self.store.data)
        changes = compute_diff(self._last_snapshot, new_snapshot)
        self._last_snapshot = new_snapshot
        if not changes:
            return

        # The dictionary is already nested under the agent's own key, so
        # diff paths like `database.schema.users.columns` are already
        # agent-qualified. Do NOT prepend agent_id.
        await self.emit(
            {
                "event": "dict.mutated",
                "agent_id": self.agent_id,
                "version": self.store.version,
                "changes": [c.to_dict() for c in changes],
            }
        )

        routed = self.router.route(self.agent_id, changes)
        for rd in routed:
            await self._send(rd)

        await self._evaluate_type_b(changes)

    async def _evaluate_type_b(self, changes: list[Change]) -> None:
        """Type B (§7.3): trigger path on self requires a peer path on another
        agent. If the peer's path is missing, emit conflict.detected + resolved
        and enqueue a `response` message to the peer's input.json."""
        peer_dicts = _load_peer_dicts(self.peers)
        for ch in changes:
            if ch.op == "delete":
                continue
            matches = evaluate_rules(
                trigger_agent=self.agent_id,
                change_path=ch.path,
                change_value=ch.new,
                peer_dicts=peer_dicts,
            )
            for m in matches:
                await self._fire_type_b(m)

    async def _fire_type_b(self, m: RuleMatch) -> None:
        rule = m.rule
        conflict_id = f"cf-{uuid.uuid4().hex[:10]}"
        await self.emit(
            {
                "event": "conflict.detected",
                "conflict_id": conflict_id,
                "path": m.trigger_path,
                "parties": [
                    {"agent_id": rule.trigger_agent, "value": m.trigger_value},
                    {"agent_id": rule.required_peer_agent, "value": None},
                ],
                "incoming_message_id": f"rule:{rule.id}",
            }
        )
        resolution_message_id = f"msg-{uuid.uuid4().hex[:12]}"
        loser = (
            rule.required_peer_agent
            if rule.winner == rule.trigger_agent
            else rule.trigger_agent
        )
        reason = (
            f"Type B rule `{rule.id}`: {rule.required_peer_agent} missing "
            f"{m.required_peer_path}"
        )
        await self.emit(
            {
                "event": "conflict.resolved",
                "conflict_id": conflict_id,
                "winner": rule.winner,
                "loser": loser,
                "reason": reason,
                "resolution_message_id": resolution_message_id,
            }
        )
        # Write a response-type message to the loser's input.json so its
        # scripted agent can act on the resolution, and emit the matching
        # message.sent so the overlay sees the courier.
        peer_dir = self.peers.get(rule.required_peer_agent)
        if peer_dir is not None:
            payload = {
                "message_id": resolution_message_id,
                "from": self.agent_id,
                "to": rule.required_peer_agent,
                "type": "response",
                "scope": m.trigger_path,
                "changes": [],
                "priority": "high",
                "correlation_id": conflict_id,
                "resolution_message": m.resolution_message,
                "required_peer_path": m.required_peer_path,
            }
            _append_to_queue(peer_dir / "input.json", payload)
            byte_size = len(json.dumps(payload).encode("utf-8"))
            await self.emit(
                {
                    "event": "message.sent",
                    "message_id": resolution_message_id,
                    "from": self.agent_id,
                    "to": rule.required_peer_agent,
                    "scope": m.trigger_path,
                    "diff_summary": {"paths_changed": 0, "bytes": byte_size},
                    "priority": "high",
                    "correlation_id": conflict_id,
                }
            )

    async def _send(self, rd: RoutedDiff) -> None:
        message_id = f"msg-{uuid.uuid4().hex[:12]}"
        payload = {
            "message_id": message_id,
            "from": self.agent_id,
            "to": rd.target,
            "scope": rd.scope,
            "changes": [c.to_dict() for c in rd.changes],
            "priority": rd.priority,
            "correlation_id": None,
        }
        # enqueue on peer input.json
        peer_dir = self.peers.get(rd.target)
        if peer_dir is not None:
            _append_to_queue(peer_dir / "input.json", payload)

        byte_size = len(json.dumps(payload).encode("utf-8"))
        await self.emit(
            {
                "event": "message.sent",
                "message_id": message_id,
                "from": self.agent_id,
                "to": rd.target,
                "scope": rd.scope,
                "diff_summary": {
                    "paths_changed": len(rd.changes),
                    "bytes": byte_size,
                },
                "priority": rd.priority,
                "correlation_id": None,
            }
        )

    # ------------------------------------------------ incoming -> deliver

    async def drain_input(self) -> None:
        """Pop pending messages from input.json, emit delivered + run conflict."""
        if not self._input_path.exists():
            return
        with self._input_path.open("r", encoding="utf-8") as f:
            envelope = json.load(f)
        queue = envelope.get("queue", [])
        if not queue:
            return
        # Drain all
        envelope["queue"] = []
        atomic_write_json(self._input_path, envelope)

        for msg in queue:
            await self.emit(
                {
                    "event": "message.delivered",
                    "message_id": msg["message_id"],
                    "from": msg["from"],
                    "to": msg["to"],
                    "latency_ms": 0,
                }
            )
            await self._apply_incoming(msg)

    async def _apply_incoming(self, msg: dict[str, Any]) -> None:
        for ch in msg.get("changes", []):
            own_value = self.store.get(ch["path"])
            if own_value is None:
                continue  # nothing to conflict with
            conflict = self.resolver.detect(
                path=ch["path"],
                incoming_value=ch["new"],
                own_value=own_value,
                incoming_agent=msg["from"],
                own_agent=self.agent_id,
                incoming_message_id=msg["message_id"],
                conflict_id=f"cf-{uuid.uuid4().hex[:10]}",
            )
            if conflict is None:
                continue

            await self.emit(
                {
                    "event": "conflict.detected",
                    "conflict_id": conflict.conflict_id,
                    "path": conflict.path,
                    "parties": conflict.parties,
                    "incoming_message_id": conflict.incoming_message_id,
                }
            )
            resolution_id = f"msg-{uuid.uuid4().hex[:12]}"
            resolution = self.resolver.resolve(conflict, resolution_message_id=resolution_id)
            await self.emit(
                {
                    "event": "conflict.resolved",
                    "conflict_id": resolution.conflict_id,
                    "winner": resolution.winner,
                    "loser": resolution.loser,
                    "reason": resolution.reason,
                    "resolution_message_id": resolution.resolution_message_id,
                }
            )


# ---------------------------------------------------------------- helpers

def _strip_meta(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in (data or {}).items() if k != "_meta"}


def _load_peer_dicts(peers: dict[str, Path]) -> dict[str, dict[str, Any]]:
    """Read each peer's dictionary.json. Missing files -> empty dict. The
    returned shape matches the on-disk JSON (including the top-level
    agent_id key), which is what `evaluate_rules` expects."""
    out: dict[str, dict[str, Any]] = {}
    for peer_id, peer_dir in peers.items():
        path = peer_dir / "dictionary.json"
        if not path.exists():
            out[peer_id] = {}
            continue
        try:
            with path.open("r", encoding="utf-8") as f:
                out[peer_id] = json.load(f)
        except (OSError, json.JSONDecodeError):
            out[peer_id] = {}
    return out


def _append_to_queue(path: Path, msg: dict[str, Any]) -> None:
    path = Path(path)
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            envelope = json.load(f)
    else:
        envelope = {"queue": []}
    envelope.setdefault("queue", []).append(msg)
    atomic_write_json(path, envelope)
