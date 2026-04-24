# AgentMesh WebSocket Event Schema

> **Canonical source of truth:** [`mesh/schemas/events.py`](../mesh/schemas/events.py) (pydantic v2) → [`mesh/schemas/events.schema.json`](../mesh/schemas/events.schema.json) (JSON Schema generated from it).
>
> **Version:** v1.1 (flat envelope, UPPERCASE agent states).
>
> TypeScript mirrors live at [`extension/src/types/events.ts`](../extension/src/types/events.ts) and [`extension/webview-ui/src/types/events.ts`](../extension/webview-ui/src/types/events.ts). These must stay in sync with the pydantic models.
>
> The sections below are a high-level narrative; **the pydantic models are authoritative** for field names, types, and validation rules.

## Connection

- URL: `ws://localhost:9900`
- Protocol: WebSocket (RFC 6455)
- Wire format: UTF-8 JSON, one event per message frame
- Server: [`mesh/ws_server.py`](../mesh/ws_server.py)
- Client: extension [`src/ws_client.ts`](../extension/src/ws_client.ts); overlay webview consumes via `postMessage`
- Reconnection: client reconnects on drop with exponential backoff (1s, 2s, 4s, max 8s)
- The server tees every event to `.agentmesh/events/session.jsonl` for replay / tests

## Event envelope (all events share these fields)

```json
{
  "event": "agent.state.changed",
  "v": "1.0",
  "seq": 42,
  "ts": "2026-04-21T10:30:15.123Z",
  "session_id": "sess-20260421-103015",
  "data": { ... event-specific payload ... }
}
```

- `event`: event type string (see table below)
- `v`: schema version — `"1.0"` for this spec
- `seq`: monotonic per-session sequence number starting at 1
- `ts`: ISO 8601 UTC with millisecond precision
- `session_id`: stable for the lifetime of one AgentMesh run
- `data`: event-specific payload, structure defined per event below

## Event types (complete list)

| Event | When emitted | Payload section |
|---|---|---|
| `mesh.session.started` | First thing after WebSocket server starts | §1 |
| `mesh.session.ended` | Last thing before server shuts down | §2 |
| `agent.state.changed` | A Mini Agent transitions IDLE ↔ WORKING ↔ BLOCKED ↔ COMPLETED | §3 |
| `dict.mutated` | An agent's `dictionary.json` changed | §4 |
| `message.sent` | A Mini Agent wrote a message to a peer's `input.json` | §5 |
| `message.delivered` | Target Mini Agent processed a message from its queue | §6 |
| `conflict.detected` | Conflict Detector flagged incompatible changes | §7 |
| `conflict.resolved` | Priority table picked a winner, loser notified | §8 |
| `metrics.tick` | 1 Hz heartbeat with running counters | §9 |

## §1 `mesh.session.started`

```json
{
  "event": "mesh.session.started",
  "v": "1.0", "seq": 1, "ts": "2026-04-21T10:30:00.000Z",
  "session_id": "sess-20260421-103000",
  "data": {
    "agents": [
      { "id": "backend",  "domain": "backend",  "display_name": "Backend" },
      { "id": "frontend", "domain": "frontend", "display_name": "Frontend" },
      { "id": "database", "domain": "database", "display_name": "Database" }
    ],
    "dependency_map_hash": "sha256:abc123..."
  }
}
```

## §2 `mesh.session.ended`

```json
{
  "event": "mesh.session.ended",
  "v": "1.0", "seq": 999, "ts": "2026-04-21T10:31:30.000Z",
  "session_id": "sess-20260421-103000",
  "data": {
    "duration_ms": 90000,
    "totals": {
      "messages": 4,
      "conflicts_detected": 1,
      "conflicts_resolved": 1,
      "dict_mutations": 8,
      "bytes_exchanged": 4820,
      "estimated_tokens_saved_pct": 0.68
    }
  }
}
```

## §3 `agent.state.changed`

```json
{
  "event": "agent.state.changed",
  "v": "1.0", "seq": 2, "ts": "2026-04-21T10:30:05.000Z",
  "session_id": "sess-20260421-103000",
  "data": {
    "agent_id": "database",
    "old_state": "idle",
    "new_state": "working",
    "current_task": "Adding users table schema"
  }
}
```

States: `"idle" | "working" | "blocked" | "completed"`.

## §4 `dict.mutated`

```json
{
  "event": "dict.mutated",
  "v": "1.0", "seq": 3, "ts": "2026-04-21T10:30:06.000Z",
  "session_id": "sess-20260421-103000",
  "data": {
    "agent_id": "database",
    "version_from": 0,
    "version_to": 1,
    "changes": [
      {
        "path": "database.schema.users.columns",
        "op": "add",
        "old": null,
        "new": ["id", "name", "email"]
      }
    ]
  }
}
```

- `op`: `"add" | "modify" | "delete"`
- `path`: dot-separated, with route paths preserved verbatim (e.g. `backend.routes./api/users.auth_required`)

## §5 `message.sent`

```json
{
  "event": "message.sent",
  "v": "1.0", "seq": 4, "ts": "2026-04-21T10:30:07.000Z",
  "session_id": "sess-20260421-103000",
  "data": {
    "message_id": "msg-20260421-database-001",
    "from": "database",
    "to": "backend",
    "type": "state_update",
    "priority": "normal",
    "scope": "database.schema.users",
    "summary": "Database added users table with columns [id, name, email]",
    "size_bytes": 420
  }
}
```

- `type`: `"state_update" | "request" | "response" | "signal"`
- `priority`: `"blocking" | "high" | "normal" | "low"`

## §6 `message.delivered`

```json
{
  "event": "message.delivered",
  "v": "1.0", "seq": 5, "ts": "2026-04-21T10:30:08.000Z",
  "session_id": "sess-20260421-103000",
  "data": {
    "message_id": "msg-20260421-database-001",
    "to": "backend",
    "processing_ms": 42
  }
}
```

## §7 `conflict.detected`

```json
{
  "event": "conflict.detected",
  "v": "1.0", "seq": 6, "ts": "2026-04-21T10:30:45.000Z",
  "session_id": "sess-20260421-103000",
  "data": {
    "conflict_id": "conf-001",
    "key_path": "backend.routes./api/users.auth_required",
    "agents": ["backend", "frontend"],
    "values": {
      "backend":  { "value": true,  "version": 4, "reason": "Security — protect PII" },
      "frontend": { "value": false, "version": 2, "reason": "Built call without auth header" }
    },
    "strategy": "priority_table"
  }
}
```

## §8 `conflict.resolved`

```json
{
  "event": "conflict.resolved",
  "v": "1.0", "seq": 7, "ts": "2026-04-21T10:30:46.000Z",
  "session_id": "sess-20260421-103000",
  "data": {
    "conflict_id": "conf-001",
    "winner": "backend",
    "loser":  "frontend",
    "applied_value": true,
    "follow_up_message_id": "msg-20260421-resolver-002",
    "rationale": "Priority table: backend > frontend on route_auth_changes"
  }
}
```

## §9 `metrics.tick`

Emitted at 1 Hz during an active session. Purely for the overlay's counter animations.

```json
{
  "event": "metrics.tick",
  "v": "1.0", "seq": 50, "ts": "2026-04-21T10:30:50.000Z",
  "session_id": "sess-20260421-103000",
  "data": {
    "messages_sent": 3,
    "messages_delivered": 3,
    "conflicts_open": 0,
    "conflicts_resolved_total": 1,
    "dict_mutations_total": 5,
    "bytes_exchanged": 2140,
    "estimated_tokens_saved_pct": 0.64
  }
}
```

`estimated_tokens_saved_pct` is a simple model: sum of bytes in filtered diffs (what AgentMesh transmits) vs. sum of bytes in full-context transfers that would be needed without path-filtered subscriptions (naive baseline = full dictionary size × number of recipients). Formula documented in `mesh/metrics.py`.

## Error handling

- On malformed JSON from server: client logs, stays connected, skips the frame.
- On unknown `event` type: client logs warning, skips (forward-compat).
- On missing required field: client logs error and continues.
- Server never closes the connection except during shutdown; all errors are logged server-side.

## Schema validation

The authoritative JSON Schema at `mesh/schemas/events.schema.json` is generated from the pydantic models. The overlay can run the same schema through `ajv` for debug assertions.

**Any field change requires updating:**
1. pydantic model in `mesh/schemas/events.py`
2. Regenerated JSON Schema in `mesh/schemas/events.schema.json`
3. TypeScript types in `extension/src/types/events.ts` (mirror the pydantic model)
4. This document

## Versioning

Bump `v` to `1.1`, `2.0`, etc. on any breaking change. Non-breaking (additive) changes increment the minor.

`v: "1.1"` is the current frozen wire format.
