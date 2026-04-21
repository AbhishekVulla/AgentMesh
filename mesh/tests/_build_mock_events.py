"""Author the canonical mock_events.jsonl.

This is a fixture builder, not a runtime tool. It constructs each event
through the pydantic models in ``mesh.schemas.events`` so anything committed
to ``mesh/mock_events.jsonl`` is guaranteed schema-valid.

Source timeline: docs/DEMO_SCENARIO.md.

Run with::

    python -m mesh.tests._build_mock_events

…from the repo root. Re-run whenever the scenario doc changes.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mesh.schemas.events import (
    AgentDescriptor,
    AgentStateChanged,
    Change,
    ConflictDetected,
    ConflictParty,
    ConflictResolved,
    DictMutated,
    DiffSummary,
    EventAdapter,
    MeshSessionEnded,
    MeshSessionStarted,
    MessageDelivered,
    MessageSent,
    MetricsTick,
    SessionTotals,
)


SESSION_ID = "sess-fixture-01"
SESSION_START = datetime(2026, 4, 21, 10, 0, 0, tzinfo=timezone.utc)


def ts(t_seconds: float) -> str:
    """Return ISO-8601 UTC ms-precision timestamp 't_seconds' after start."""
    dt = SESSION_START + timedelta(seconds=t_seconds)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


# ---------------------------------------------------------------- helpers


def env(seq: int, t: float) -> dict:
    return {"seq": seq, "ts": ts(t), "session_id": SESSION_ID}


def tick(seq: int, t: float, messages: int, conflicts: int, bytes_: int, pct: float) -> MetricsTick:
    return MetricsTick(
        **env(seq, t),
        messages_total=messages,
        conflicts_total=conflicts,
        bytes_exchanged_total=bytes_,
        estimated_tokens_saved_pct=pct,
    )


# ------------------------------------------------------------ build list

def build() -> list:
    events: list = []
    s = 0
    # Cumulative metrics (grow monotonically between ticks).
    msgs = 0
    confs = 0
    bx = 0

    def T() -> MetricsTick:
        # Cheap "tokens saved" heuristic that climbs with activity.
        saved = min(78.50, (msgs * 10.0) + (confs * 5.0))
        return tick(next_seq(), pending_t[0], msgs, confs, bx, round(saved, 2))

    pending_t = [0.0]  # mutable holder to let T() pick up latest t without arg plumbing

    def next_seq() -> int:
        nonlocal s
        v = s
        s += 1
        return v

    # seq 0 — session started
    events.append(
        MeshSessionStarted(
            **env(next_seq(), 0.000),
            agents=[
                AgentDescriptor(id="backend",  role="Backend API",     exposes=["routes.*", "models.*", "auth.*"]),
                AgentDescriptor(id="frontend", role="Frontend UI",     exposes=["api_calls.*"]),
                AgentDescriptor(id="database", role="Database schema", exposes=["schema.*"]),
            ],
            config_path="demo/config.yaml",
        )
    )

    # seq 1 — initial zero tick
    pending_t[0] = 0.050
    events.append(T())

    # seq 2 — database begins
    events.append(
        AgentStateChanged(
            **env(next_seq(), 1.000),
            agent_id="database",
            **{"from": "IDLE"},  # alias field
            to="WORKING",
            current_task="Defining users table schema",
        )
    )
    pending_t[0] = 1.050
    events.append(T())

    # seq 4 — database dict.mutated: add schema.users
    events.append(
        DictMutated(
            **env(next_seq(), 2.000),
            agent_id="database",
            version=1,
            changes=[
                Change(
                    path="database.schema.users",
                    op="add",
                    old=None,
                    new={"columns": ["id", "name", "email", "created_at"]},
                )
            ],
        )
    )

    # seq 5 — msg-001 database → backend
    msg_bytes = 120
    events.append(
        MessageSent(
            **env(next_seq(), 2.050),
            message_id="msg-001",
            **{"from": "database"},
            to="backend",
            scope="database.schema.users",
            diff_summary=DiffSummary(paths_changed=1, bytes=msg_bytes),
            priority="normal",
            correlation_id=None,
        )
    )
    msgs += 1
    bx += msg_bytes
    pending_t[0] = 2.100
    events.append(T())
    pending_t[0] = 3.000
    events.append(T())

    # seq 8 — backend begins
    events.append(
        AgentStateChanged(
            **env(next_seq(), 4.000),
            agent_id="backend",
            **{"from": "IDLE"},
            to="WORKING",
            current_task="Aligning User model with schema",
        )
    )
    pending_t[0] = 4.050
    events.append(T())

    # seq 10 — delivery of msg-001
    events.append(
        MessageDelivered(
            **env(next_seq(), 5.000),
            message_id="msg-001",
            **{"from": "database"},
            to="backend",
            latency_ms=2950,
        )
    )
    pending_t[0] = 5.050
    events.append(T())

    # seq 12 — backend dict.mutated: add models.User
    events.append(
        DictMutated(
            **env(next_seq(), 6.000),
            agent_id="backend",
            version=1,
            changes=[
                Change(
                    path="backend.models.User",
                    op="add",
                    old=None,
                    new={
                        "fields": {
                            "id": "int",
                            "name": "string",
                            "email": "string",
                            "created_at": "datetime",
                        }
                    },
                )
            ],
        )
    )

    # seq 13 — msg-002 backend → database
    msg_bytes = 180
    events.append(
        MessageSent(
            **env(next_seq(), 6.050),
            message_id="msg-002",
            **{"from": "backend"},
            to="database",
            scope="backend.models.User",
            diff_summary=DiffSummary(paths_changed=1, bytes=msg_bytes),
            priority="normal",
            correlation_id=None,
        )
    )
    msgs += 1
    bx += msg_bytes
    pending_t[0] = 6.100
    events.append(T())

    # seq 15 — delivery msg-002
    events.append(
        MessageDelivered(
            **env(next_seq(), 6.500),
            message_id="msg-002",
            **{"from": "backend"},
            to="database",
            latency_ms=450,
        )
    )
    pending_t[0] = 7.000
    events.append(T())

    # seq 17 — backend dict.mutated: add routes./api/users
    events.append(
        DictMutated(
            **env(next_seq(), 8.000),
            agent_id="backend",
            version=2,
            changes=[
                Change(
                    path="backend.routes./api/users",
                    op="add",
                    old=None,
                    new={"method": "GET", "auth_required": False},
                )
            ],
        )
    )

    # seq 18 — msg-003 backend → frontend
    msg_bytes = 140
    events.append(
        MessageSent(
            **env(next_seq(), 8.050),
            message_id="msg-003",
            **{"from": "backend"},
            to="frontend",
            scope="backend.routes./api/users",
            diff_summary=DiffSummary(paths_changed=1, bytes=msg_bytes),
            priority="normal",
            correlation_id=None,
        )
    )
    msgs += 1
    bx += msg_bytes
    pending_t[0] = 8.100
    events.append(T())
    pending_t[0] = 9.000
    events.append(T())

    # seq 21 — frontend begins
    events.append(
        AgentStateChanged(
            **env(next_seq(), 10.000),
            agent_id="frontend",
            **{"from": "IDLE"},
            to="WORKING",
            current_task="Wiring fetch('/api/users') call",
        )
    )
    pending_t[0] = 10.050
    events.append(T())

    # seq 23 — delivery msg-003
    events.append(
        MessageDelivered(
            **env(next_seq(), 11.000),
            message_id="msg-003",
            **{"from": "backend"},
            to="frontend",
            latency_ms=2950,
        )
    )
    pending_t[0] = 11.050
    events.append(T())

    # seq 25 — frontend dict.mutated: add api_calls
    events.append(
        DictMutated(
            **env(next_seq(), 12.000),
            agent_id="frontend",
            version=1,
            changes=[
                Change(
                    path="frontend.api_calls./api/users",
                    op="add",
                    old=None,
                    new={"method": "GET", "headers": {}},
                )
            ],
        )
    )

    # seq 26 — msg-004 frontend → backend
    msg_bytes = 120
    events.append(
        MessageSent(
            **env(next_seq(), 12.050),
            message_id="msg-004",
            **{"from": "frontend"},
            to="backend",
            scope="frontend.api_calls./api/users",
            diff_summary=DiffSummary(paths_changed=1, bytes=msg_bytes),
            priority="normal",
            correlation_id=None,
        )
    )
    msgs += 1
    bx += msg_bytes
    pending_t[0] = 12.100
    events.append(T())

    # seq 28 — delivery msg-004
    events.append(
        MessageDelivered(
            **env(next_seq(), 12.500),
            message_id="msg-004",
            **{"from": "frontend"},
            to="backend",
            latency_ms=450,
        )
    )
    pending_t[0] = 13.000
    events.append(T())
    pending_t[0] = 14.000
    events.append(T())

    # seq 31 — backend dict.mutated: modify auth_required false→true
    events.append(
        DictMutated(
            **env(next_seq(), 15.000),
            agent_id="backend",
            version=3,
            changes=[
                Change(
                    path="backend.routes./api/users.auth_required",
                    op="modify",
                    old=False,
                    new=True,
                )
            ],
        )
    )

    # seq 32 — msg-005 backend → frontend, HIGH priority (security promote)
    msg_bytes = 60
    events.append(
        MessageSent(
            **env(next_seq(), 15.050),
            message_id="msg-005",
            **{"from": "backend"},
            to="frontend",
            scope="backend.routes./api/users.auth_required",
            diff_summary=DiffSummary(paths_changed=1, bytes=msg_bytes),
            priority="high",
            correlation_id=None,
        )
    )
    msgs += 1
    bx += msg_bytes
    pending_t[0] = 15.100
    events.append(T())
    pending_t[0] = 16.000
    events.append(T())

    # seq 35 — delivery msg-005
    events.append(
        MessageDelivered(
            **env(next_seq(), 16.500),
            message_id="msg-005",
            **{"from": "backend"},
            to="frontend",
            latency_ms=1450,
        )
    )

    # seq 36 — conflict detected (by frontend's mini agent)
    events.append(
        ConflictDetected(
            **env(next_seq(), 17.000),
            conflict_id="cf-001",
            path="backend.routes./api/users.auth_required",
            parties=[
                ConflictParty(agent_id="backend",  value=True),
                ConflictParty(agent_id="frontend", value=False),
            ],
            incoming_message_id="msg-005",
        )
    )
    confs += 1
    pending_t[0] = 17.050
    events.append(T())

    # seq 38 — conflict resolved via priority table
    events.append(
        ConflictResolved(
            **env(next_seq(), 18.000),
            conflict_id="cf-001",
            winner="backend",
            loser="frontend",
            reason="route_auth_changes priority table: backend > frontend > database",
            resolution_message_id="msg-006",
        )
    )

    # seq 39 — msg-006 backend → frontend (response, correlated to msg-005)
    msg_bytes = 80
    events.append(
        MessageSent(
            **env(next_seq(), 18.050),
            message_id="msg-006",
            **{"from": "backend"},
            to="frontend",
            scope="backend.routes./api/users.auth_required",
            diff_summary=DiffSummary(paths_changed=1, bytes=msg_bytes),
            priority="high",
            correlation_id="msg-005",
        )
    )
    msgs += 1
    bx += msg_bytes
    pending_t[0] = 18.100
    events.append(T())

    # seq 41 — delivery msg-006
    events.append(
        MessageDelivered(
            **env(next_seq(), 18.500),
            message_id="msg-006",
            **{"from": "backend"},
            to="frontend",
            latency_ms=450,
        )
    )
    pending_t[0] = 19.000
    events.append(T())

    # seq 43 — frontend dict.mutated: add Authorization header
    events.append(
        DictMutated(
            **env(next_seq(), 20.000),
            agent_id="frontend",
            version=2,
            changes=[
                Change(
                    path="frontend.api_calls./api/users.headers",
                    op="modify",
                    old={},
                    new={"Authorization": "Bearer {{token}}"},
                )
            ],
        )
    )

    # seq 44 — msg-007 frontend → backend (post-resolution update)
    msg_bytes = 160
    events.append(
        MessageSent(
            **env(next_seq(), 20.050),
            message_id="msg-007",
            **{"from": "frontend"},
            to="backend",
            scope="frontend.api_calls./api/users.headers",
            diff_summary=DiffSummary(paths_changed=1, bytes=msg_bytes),
            priority="normal",
            correlation_id=None,
        )
    )
    msgs += 1
    bx += msg_bytes
    pending_t[0] = 20.100
    events.append(T())
    pending_t[0] = 21.000
    events.append(T())

    # seq 47 — backend → COMPLETED
    events.append(
        AgentStateChanged(
            **env(next_seq(), 22.000),
            agent_id="backend",
            **{"from": "WORKING"},
            to="COMPLETED",
            current_task="Routes + models finalized",
        )
    )

    # seq 48 — delivery msg-007
    events.append(
        MessageDelivered(
            **env(next_seq(), 22.050),
            message_id="msg-007",
            **{"from": "frontend"},
            to="backend",
            latency_ms=2000,
        )
    )
    pending_t[0] = 22.100
    events.append(T())
    pending_t[0] = 23.000
    events.append(T())

    # seq 51 — database → COMPLETED
    events.append(
        AgentStateChanged(
            **env(next_seq(), 24.000),
            agent_id="database",
            **{"from": "WORKING"},
            to="COMPLETED",
            current_task="Schema stable",
        )
    )
    pending_t[0] = 24.050
    events.append(T())

    # seq 53 — frontend → COMPLETED
    events.append(
        AgentStateChanged(
            **env(next_seq(), 25.000),
            agent_id="frontend",
            **{"from": "WORKING"},
            to="COMPLETED",
            current_task="Auth headers wired",
        )
    )
    pending_t[0] = 25.050
    events.append(T())

    # seq 55 — session ended
    total_events = len(events) + 1
    events.append(
        MeshSessionEnded(
            **env(next_seq(), 26.000),
            reason="completed",
            totals=SessionTotals(
                events_emitted=total_events,
                messages_routed=msgs,
                conflicts=confs,
                bytes_exchanged=bx,
                duration_ms=26000,
            ),
        )
    )

    return events


def main() -> None:
    events = build()
    # Round-trip through the adapter to double-check discriminated-union validity.
    for e in events:
        EventAdapter.validate_python(e.model_dump(by_alias=True))

    out = Path(__file__).resolve().parents[1] / "mock_events.jsonl"
    with out.open("w", encoding="utf-8", newline="\n") as f:
        for e in events:
            f.write(json.dumps(e.model_dump(by_alias=True), ensure_ascii=False))
            f.write("\n")
    print(f"wrote {len(events)} events -> {out}")


if __name__ == "__main__":
    main()
