"""Authoritative pydantic-v2 event models.

Source of truth for the WebSocket event contract described in
``docs/WEBSOCKET_SCHEMA.md``. The TypeScript types the P2 overlay consumes
are generated from ``Event.model_json_schema()`` → ``events.schema.json``.

**Do not edit these fields without updating WEBSOCKET_SCHEMA.md and bumping
the schema version in the commit message prefix `sync-needed:`.**
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


# --------------------------------------------------------------- Enums / lits

AgentState = Literal["IDLE", "WORKING", "BLOCKED", "COMPLETED"]
Priority = Literal["low", "normal", "high"]
Op = Literal["add", "modify", "delete"]
SessionEndReason = Literal["completed", "aborted", "error"]


# ------------------------------------------------------------ Nested payloads


class AgentDescriptor(BaseModel):
    """Describes an agent in `mesh.session.started`."""

    model_config = ConfigDict(extra="forbid")

    id: str
    role: str
    exposes: list[str]


class Change(BaseModel):
    """One entry in `dict.mutated.changes[]`."""

    model_config = ConfigDict(extra="forbid")

    path: str
    op: Op
    old: Any = None
    new: Any = None


class ConflictParty(BaseModel):
    """One side of a conflict (`conflict.detected.parties[]`)."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    value: Any


class DiffSummary(BaseModel):
    """Compact summary attached to `message.sent.diff_summary`."""

    model_config = ConfigDict(extra="forbid")

    paths_changed: int = Field(ge=0)
    bytes: int = Field(ge=0)


class SessionTotals(BaseModel):
    """Closing tallies attached to `mesh.session.ended.totals`."""

    model_config = ConfigDict(extra="forbid")

    events_emitted: int = Field(ge=0)
    messages_routed: int = Field(ge=0)
    conflicts: int = Field(ge=0)
    bytes_exchanged: int = Field(ge=0)
    duration_ms: int = Field(ge=0)


# ----------------------------------------------------------- Common envelope


class _Envelope(BaseModel):
    """Fields present on every event."""

    model_config = ConfigDict(extra="forbid")

    seq: int = Field(ge=0)
    ts: str  # ISO-8601 UTC, millisecond precision, suffix "Z"
    session_id: str


# ------------------------------------------------------------- Event variants


class MeshSessionStarted(_Envelope):
    event: Literal["mesh.session.started"] = "mesh.session.started"
    agents: list[AgentDescriptor]
    config_path: str


class MeshSessionEnded(_Envelope):
    event: Literal["mesh.session.ended"] = "mesh.session.ended"
    reason: SessionEndReason
    totals: SessionTotals


class AgentStateChanged(_Envelope):
    event: Literal["agent.state.changed"] = "agent.state.changed"
    agent_id: str
    from_: AgentState = Field(alias="from")
    to: AgentState
    current_task: str | None = None

    # Allow using both .from_ and serialization via alias "from".
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class DictMutated(_Envelope):
    event: Literal["dict.mutated"] = "dict.mutated"
    agent_id: str
    version: int = Field(ge=1)
    changes: list[Change]


class MessageSent(_Envelope):
    event: Literal["message.sent"] = "message.sent"
    message_id: str
    from_: str = Field(alias="from")
    to: str
    scope: str
    diff_summary: DiffSummary
    priority: Priority = "normal"
    correlation_id: str | None = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class MessageDelivered(_Envelope):
    event: Literal["message.delivered"] = "message.delivered"
    message_id: str
    from_: str = Field(alias="from")
    to: str
    latency_ms: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ConflictDetected(_Envelope):
    event: Literal["conflict.detected"] = "conflict.detected"
    conflict_id: str
    path: str
    parties: list[ConflictParty]
    incoming_message_id: str


class ConflictResolved(_Envelope):
    event: Literal["conflict.resolved"] = "conflict.resolved"
    conflict_id: str
    winner: str
    loser: str
    reason: str
    resolution_message_id: str


class MetricsTick(_Envelope):
    event: Literal["metrics.tick"] = "metrics.tick"
    messages_total: int = Field(ge=0)
    conflicts_total: int = Field(ge=0)
    bytes_exchanged_total: int = Field(ge=0)
    estimated_tokens_saved_pct: float = Field(ge=0.0, le=100.0)


# ------------------------------------------------------- Discriminated union


Event = Annotated[
    Union[
        MeshSessionStarted,
        MeshSessionEnded,
        AgentStateChanged,
        DictMutated,
        MessageSent,
        MessageDelivered,
        ConflictDetected,
        ConflictResolved,
        MetricsTick,
    ],
    Field(discriminator="event"),
]


EventAdapter: TypeAdapter[Event] = TypeAdapter(Event)


def event_json_schema() -> dict[str, Any]:
    """Return the top-level JSON Schema for any Event (discriminated union)."""
    return EventAdapter.json_schema()
