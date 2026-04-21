"""`AgentMeshClient` — the library API a major agent uses to join the mesh.

This is the companion to `mesh.cli`. It wraps `DictStore` so external tools
(the CLI, a pytest fixture, a notebook, a Claude Code hook) can:

    client = AgentMeshClient(agent_id="backend")
    client.register(role="backend")
    client.set("routes./api/users.auth_required", True)
    msgs = client.drain_input()

No network calls. Everything is file-based under
`.agentmesh/agents/<agent_id>/`, which is what the bus' Mini Agent watches.
The bus picks up the mutations via its mtime-polling session loop.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mesh.dict_store import DictStore, atomic_write_json, tokenize_dotpath, utc_now_iso


class AgentMeshClient:
    """File-based client for one major agent."""

    def __init__(self, agent_id: str, base_dir: Path | str = ".agentmesh/agents") -> None:
        self.agent_id = agent_id
        self.base_dir = Path(base_dir)
        self.agent_dir = self.base_dir / agent_id
        self.dict_path = self.agent_dir / "dictionary.json"
        self.input_path = self.agent_dir / "input.json"
        self.summary_path = self.agent_dir / "summary.json"
        self._store = DictStore(self.dict_path, agent_id=agent_id)

    # ----------------------------------------------------------- lifecycle

    def register(self, role: str | None = None) -> int:
        """Create the agent's directory and seed dictionary.json / input.json.

        Idempotent. Returns the dictionary's current version.
        """
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        self._store.load()
        # Seed role into _meta if caller provided one; do not clobber existing.
        data = dict(self._store.data)
        meta = dict(data.get("_meta", {}))
        meta.setdefault("agent_id", self.agent_id)
        if role:
            meta["role"] = role
        meta.setdefault("registered_at", utc_now_iso())
        data["_meta"] = meta
        self._store.save(data)
        if not self.input_path.exists():
            atomic_write_json(self.input_path, {"queue": []})
        if not self.summary_path.exists():
            atomic_write_json(
                self.summary_path,
                {"state": "IDLE", "current_task": ""},
            )
        return self._store.version

    # ------------------------------------------------------------ mutation

    def set(self, dotpath: str, value: Any) -> int:
        self._store.load()
        return self._store.set(dotpath, value)

    def unset(self, dotpath: str) -> int:
        self._store.load()
        segments = tokenize_dotpath(dotpath)
        if not segments:
            raise ValueError("empty dotpath")
        data = self._store.data
        cur: Any = data
        for seg in segments[:-1]:
            if not isinstance(cur, dict) or seg not in cur:
                return self._store.version  # nothing to delete
            cur = cur[seg]
        if isinstance(cur, dict) and segments[-1] in cur:
            del cur[segments[-1]]
            return self._store.save()
        return self._store.version

    def set_state(self, state: str, current_task: str = "") -> None:
        """Flip agent.state.changed via summary.json (bus picks it up)."""
        atomic_write_json(self.summary_path, {"state": state, "current_task": current_task})

    # -------------------------------------------------------------- intake

    def drain_input(self) -> list[dict[str, Any]]:
        """Pop all pending inbound messages. Returns [] if none."""
        if not self.input_path.exists():
            return []
        with self.input_path.open("r", encoding="utf-8") as f:
            envelope = json.load(f)
        queue = envelope.get("queue", [])
        if not queue:
            return []
        envelope["queue"] = []
        atomic_write_json(self.input_path, envelope)
        return queue

    # ---------------------------------------------------------------- read

    def get(self, dotpath: str) -> Any:
        self._store.load()
        return self._store.get(dotpath)

    @property
    def version(self) -> int:
        self._store.load()
        return self._store.version

    @property
    def data(self) -> dict[str, Any]:
        self._store.load()
        return self._store.data
