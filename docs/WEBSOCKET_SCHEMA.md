# WebSocket Event Schema (G1 contract)

> **This document is frozen after Gate G1** (Day 1, first 60 min). Schema changes after that require an explicit P1+P2 sync (commit subject prefix `sync-needed:` plus Discord/iMessage).

Protocol: JSON-over-WebSocket on `ws://localhost:9900`. One event per WebSocket frame. Every event is simultaneously tee'd to `.agentmesh/events/session.jsonl` (one line per event) for replay.

## Common envelope

Every event has these fields:

| Field | Type | Description |
|---|---|---|
| `event` | string (literal) | Event type discriminator. Must be one of the `event` values below. |
| `seq` | int | Monotonically increasing per-session sequence number, starting at 0. |
| `ts` | string (ISO-8601 UTC) | Wall-clock timestamp, e.g. `"2026-04-21T10:30:00.123Z"`. |
| `session_id` | string | Stable ID for the current session (UUID4). |

Additional fields depend on the event type (below).

## Event types (complete list — 9)

All examples omit the common envelope for brevity; assume `event`, `seq`, `ts`, `session_id` are always present.

---

### 1. `mesh.session.started`

Emitted exactly once at the start of the WebSocket server's lifecycle, after all Mini Agents have registered.

```json
{
  "event": "mesh.session.started",
  "agents": [
    { "id": "backend",  "role": "Backend API",       "exposes": ["routes.*", "models.*", "auth.*"] },
    { "id": "frontend", "role": "Frontend UI",       "exposes": ["api_calls.*"] },
    { "id": "database", "role": "Database schema",   "exposes": ["schema.*"] }
  ],
  "config_path": "demo/config.yaml"
}
```

### 2. `mesh.session.ended`

Final event. Clients should close after receiving this.

```json
{
  "event": "mesh.session.ended",
  "reason": "completed",
  "totals": {
    "events_emitted": 42,
    "messages_routed": 4,
    "conflicts": 1,
    "bytes_exchanged": 1280,
    "duration_ms": 26000
  }
}
```

`reason` ∈ `"completed"` | `"aborted"` | `"error"`.

### 3. `agent.state.changed`

An agent transitioned state.

```json
{
  "event": "agent.state.changed",
  "agent_id": "backend",
  "from": "IDLE",
  "to": "WORKING",
  "current_task": "Adding /api/users route"
}
```

States: `"IDLE"` | `"WORKING"` | `"BLOCKED"` | `"COMPLETED"`.

### 4. `dict.mutated`

An agent's dictionary was mutated. Payload carries the full diff (not the full dict).

```json
{
  "event": "dict.mutated",
  "agent_id": "backend",
  "version": 3,
  "changes": [
    {
      "path": "backend.routes./api/users",
      "op":   "add",
      "old":  null,
      "new":  { "method": "GET", "auth_required": true }
    }
  ]
}
```

`op` ∈ `"add"` | `"modify"` | `"delete"`. For `"add"`, `old` is `null`. For `"delete"`, `new` is `null`. `path` segments preserve verbatim (slashes inside route paths are OK — the parser uses a tokenizer, not a naive `split(".")`).

### 5. `message.sent`

A Mini Agent routed a message to a peer via `input.json`.

```json
{
  "event": "message.sent",
  "message_id": "msg-20260421-backend-001",
  "from": "backend",
  "to":   "frontend",
  "scope": "backend.routes./api/users",
  "diff_summary": { "paths_changed": 1, "bytes": 156 },
  "priority": "normal",
  "correlation_id": null
}
```

`priority` ∈ `"low"` | `"normal"` | `"high"`. `correlation_id` is set on responses (e.g. conflict resolutions); otherwise `null`.

### 6. `message.delivered`

The target Mini Agent read the message from its `input.json`.

```json
{
  "event": "message.delivered",
  "message_id": "msg-20260421-backend-001",
  "from": "backend",
  "to":   "frontend",
  "latency_ms": 42
}
```

### 7. `conflict.detected`

The incoming scope collides with the target's own dictionary.

```json
{
  "event": "conflict.detected",
  "conflict_id": "cf-20260421-001",
  "path": "backend.routes./api/users.auth_required",
  "parties": [
    { "agent_id": "backend",  "value": true  },
    { "agent_id": "frontend", "value": false }
  ],
  "incoming_message_id": "msg-20260421-frontend-003"
}
```

### 8. `conflict.resolved`

Priority table picked a winner.

```json
{
  "event": "conflict.resolved",
  "conflict_id": "cf-20260421-001",
  "winner": "backend",
  "loser": "frontend",
  "reason": "route_auth_changes priority table: backend > frontend > database",
  "resolution_message_id": "msg-20260421-backend-004"
}
```

### 9. `metrics.tick`

Emitted at ~1 Hz, or on significant state change, whichever is sooner. Drives the metrics bar in the overlay.

```json
{
  "event": "metrics.tick",
  "messages_total": 4,
  "conflicts_total": 1,
  "bytes_exchanged_total": 1280,
  "estimated_tokens_saved_pct": 78.5
}
```

`estimated_tokens_saved_pct` is a rough heuristic: `1 - (bytes routed / bytes if full context had been passed)`. Shown as a % float, two decimals.

---

## Field notes and constraints

- **Timestamps**: always UTC, always ISO-8601 with millisecond precision, always suffixed `Z`. No offsets.
- **Sequence numbers**: start at 0, strictly increasing, gap-free within a session.
- **Agent IDs**: lowercase, kebab-allowed, no spaces. MVP uses exactly `"backend"`, `"frontend"`, `"database"`.
- **Paths**: see §4 above — `.` is the separator; route/URL slashes are part of the segment. Example: `backend.routes./api/users.method` has segments `["backend", "routes", "/api/users", "method"]`.
- **Byte counts**: UTF-8 encoded JSON byte length of the message payload (excluding envelope).
- **Versions**: per-agent monotonic ints; reset to 1 on session start.

## pydantic generation

The authoritative schema lives in [`mesh/schemas/events.py`](../mesh/schemas/events.py) (pydantic v2 `BaseModel`s with a discriminated union). A JSON Schema is generated via `pydantic.TypeAdapter(Event).json_schema()` and committed to `mesh/schemas/events.schema.json` for P2's TypeScript side to consume.

**If pydantic and this doc disagree, pydantic wins** (because P2's types are generated from it). File a `sync-needed:` commit if you spot a divergence.
