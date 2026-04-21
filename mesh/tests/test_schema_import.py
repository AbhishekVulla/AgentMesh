"""Smoke test: pydantic event models import and round-trip JSON."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mesh.schemas import Event
from mesh.schemas.events import (
    AgentStateChanged,
    EventAdapter,
    MeshSessionStarted,
    event_json_schema,
)


def test_event_union_json_schema_has_nine_variants() -> None:
    schema = event_json_schema()
    # pydantic v2 lists discriminator variants under oneOf.
    variants = schema.get("oneOf") or schema.get("anyOf") or []
    assert len(variants) == 9, f"expected 9 event variants, got {len(variants)}"


def test_agent_state_changed_round_trip() -> None:
    raw = {
        "event": "agent.state.changed",
        "seq": 2,
        "ts": "2026-04-21T10:30:00.000Z",
        "session_id": "sess-fixture",
        "agent_id": "backend",
        "from": "IDLE",
        "to": "WORKING",
        "current_task": "Adding /api/users route",
    }
    ev = EventAdapter.validate_python(raw)
    assert isinstance(ev, AgentStateChanged)
    # Serialize back with alias so the 'from' key reappears.
    dumped = ev.model_dump(by_alias=True)
    assert dumped["from"] == "IDLE"
    assert dumped["to"] == "WORKING"
    # Idempotent through JSON.
    round_tripped = EventAdapter.validate_json(json.dumps(dumped))
    assert round_tripped == ev


def test_generated_schema_file_is_committed() -> None:
    p = Path(__file__).resolve().parents[1] / "schemas" / "events.schema.json"
    assert p.exists(), "events.schema.json must be committed for P2 to consume"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert "$defs" in data or "definitions" in data or "oneOf" in data or "anyOf" in data
