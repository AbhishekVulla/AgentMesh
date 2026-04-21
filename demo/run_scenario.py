"""Drive the DEMO_SCENARIO.md timeline by mutating dictionary.json files.

Run `python -m mesh.run --config demo/config.yaml` in one terminal first;
this script pumps the 26-second timeline against the running bus from a
second terminal. The Mini Agents watch dictionary.json mtime, diff,
route, and fire the Type B rule when backend promotes auth_required.

No LLM calls. Every action is a dictionary mutation or a state flip.
"""
from __future__ import annotations

import time
from pathlib import Path

from mesh.dict_store import DictStore, atomic_write_json


ROOT = Path(".agentmesh/agents")


def write_dict(agent: str, data: dict) -> None:
    store = DictStore(ROOT / agent / "dictionary.json", agent_id=agent)
    store.load()
    store.save({**store.data, **data})


def write_state(agent: str, state: str, current_task: str = "") -> None:
    path = ROOT / agent / "summary.json"
    atomic_write_json(path, {"state": state, "current_task": current_task})
    print(f"[{agent}] -> {state} {current_task}")


def main() -> int:
    for a in ("backend", "frontend", "database"):
        (ROOT / a).mkdir(parents=True, exist_ok=True)
        atomic_write_json(
            ROOT / a / "dictionary.json",
            {"_meta": {"agent_id": a, "version": 0}},
        )
        atomic_write_json(ROOT / a / "input.json", {"queue": []})

    print("[demo] scenario start — three agents on disk")
    time.sleep(1.0)

    # T+1 database -> WORKING
    write_state("database", "WORKING", "Defining users schema")
    time.sleep(1.0)

    # T+2 database defines schema
    write_dict("database", {
        "database": {"schema": {"users": {
            "columns": ["id", "name", "email", "created_at"],
        }}},
    })
    time.sleep(2.0)

    # T+4 backend -> WORKING
    write_state("backend", "WORKING", "Aligning User model")
    time.sleep(2.0)

    # T+6 backend aligns User model
    write_dict("backend", {
        "backend": {"models": {"User": {"fields": {
            "id": "int", "name": "string", "email": "string",
            "created_at": "datetime",
        }}}},
    })
    time.sleep(2.0)

    # T+8 backend adds GET /api/users route (auth-less initially)
    write_dict("backend", {
        "backend": {
            "models": {"User": {"fields": {
                "id": "int", "name": "string", "email": "string",
                "created_at": "datetime",
            }}},
            "routes": {"/api/users": {"method": "GET", "auth_required": False}},
        },
    })
    time.sleep(2.0)

    # T+10 frontend -> WORKING
    write_state("frontend", "WORKING", "Wiring /api/users call")
    time.sleep(2.0)

    # T+12 frontend adds api_calls with empty headers. Deliberately NO
    # Authorization — this is what makes the Type B rule fire later.
    write_dict("frontend", {
        "frontend": {"api_calls": {"/api/users": {
            "method": "GET", "headers": {},
        }}},
    })
    time.sleep(3.0)

    # T+15 backend security-promotes the route (Type B trigger)
    write_dict("backend", {
        "backend": {
            "models": {"User": {"fields": {
                "id": "int", "name": "string", "email": "string",
                "created_at": "datetime",
            }}},
            "routes": {"/api/users": {"method": "GET", "auth_required": True}},
        },
    })
    time.sleep(5.0)

    # T+20 frontend applies the resolution: adds the Authorization header.
    write_dict("frontend", {
        "frontend": {"api_calls": {"/api/users": {
            "method": "GET",
            "headers": {"Authorization": "Bearer {{token}}"},
        }}},
    })
    time.sleep(2.0)

    # T+22 backend -> COMPLETED
    write_state("backend", "COMPLETED")
    time.sleep(2.0)

    # T+24 database -> COMPLETED
    write_state("database", "COMPLETED")
    time.sleep(1.0)

    # T+25 frontend -> COMPLETED
    write_state("frontend", "COMPLETED")
    time.sleep(1.0)

    print("[demo] scenario complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
