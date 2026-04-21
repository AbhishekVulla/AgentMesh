"""Drive the DEMO_SCENARIO timeline by writing dictionary.json files.

Run `python -m mesh.run --config demo/config.yaml` in one terminal, then
this script in another. The Mini Agents watch dictionary.json mtime and
emit the wire events live to every WebSocket client (including the
overlay at overlay/index.html).

No LLM calls. Every action is a dictionary mutation or a state flip.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from mesh.dict_store import DictStore, atomic_write_json


ROOT = Path(".agentmesh/agents")


def write_dict(agent: str, data: dict) -> None:
    store = DictStore(ROOT / agent / "dictionary.json", agent_id=agent)
    store.load()
    store.save({**store.data, **data})


def write_state(agent: str, state: str, current_task: str = "") -> None:
    """Emit an agent.state.changed by updating summary.json (bus picks it up
    via the session loop's input drain — for MVP we just print + sleep)."""
    path = ROOT / agent / "summary.json"
    atomic_write_json(path, {"state": state, "current_task": current_task})
    print(f"[{agent}] -> {state} {current_task}")


def main() -> int:
    for a in ("backend", "frontend", "database"):
        (ROOT / a).mkdir(parents=True, exist_ok=True)
        # Start from empty dictionary for determinism.
        atomic_write_json(ROOT / a / "dictionary.json",
                          {"_meta": {"agent_id": a, "version": 0}})
        atomic_write_json(ROOT / a / "input.json", {"queue": []})

    print("[demo] scenario start — three agents on disk")
    time.sleep(1.0)

    # T+2.0 database defines schema
    write_state("database", "WORKING", "Defining users schema")
    write_dict("database", {
        "database": {"schema": {"users": {"columns": ["id", "name", "email", "created_at"]}}},
    })
    time.sleep(3.0)

    # T+6.0 backend aligns User model
    write_state("backend", "WORKING", "Aligning User model")
    write_dict("backend", {
        "backend": {"models": {"User": {"fields": {
            "id": "int", "name": "string", "email": "string", "created_at": "datetime"}}}},
    })
    time.sleep(2.0)

    # T+8.0 backend adds GET /api/users route, auth-less
    write_dict("backend", {
        "backend": {
            "models": {"User": {"fields": {
                "id": "int", "name": "string", "email": "string", "created_at": "datetime"}}},
            "routes": {"/api/users": {"method": "GET", "auth_required": False}},
        },
    })
    time.sleep(3.0)

    # T+12.0 frontend adds API call without Authorization header
    write_state("frontend", "WORKING", "Wiring /api/users call")
    write_dict("frontend", {
        "frontend": {"api_calls": {"/api/users": {"method": "GET", "headers": {}}}},
    })
    time.sleep(3.0)

    # T+15.0 backend security-promotes the route
    write_dict("backend", {
        "backend": {
            "models": {"User": {"fields": {
                "id": "int", "name": "string", "email": "string", "created_at": "datetime"}}},
            "routes": {"/api/users": {"method": "GET", "auth_required": True}},
        },
    })
    time.sleep(4.0)

    # T+20.0 frontend applies resolution: auth header
    write_dict("frontend", {
        "frontend": {"api_calls": {"/api/users": {
            "method": "GET",
            "headers": {"Authorization": "Bearer {{token}}"},
        }}},
    })
    time.sleep(2.0)

    write_state("backend", "COMPLETED")
    write_state("database", "COMPLETED")
    write_state("frontend", "COMPLETED")
    print("[demo] scenario complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
