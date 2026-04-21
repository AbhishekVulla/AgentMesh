# SYNC NEEDED — WebSocket event schema format

**Opened:** 2026-04-21 by P1 (Ishaan)
**Audience:** P2 (Abhi)
**Blocks:** pre-integration — do not land on `main` until resolved.

## The mismatch

`docs/WEBSOCKET_SCHEMA.md` (frozen under Gate G1) specifies **enveloped v1.0** events:

```json
{"event": "agent.state.changed", "v": "1.0", "seq": 42,
 "ts": "2026-04-21T10:00:00Z", "session_id": "sess-...",
 "data": {"agent_id": "backend", "from": "idle", "to": "working", ...}}
```

`mesh/schemas/events.py` (pydantic models authored Day 1) emits **flat** events:

```json
{"event": "agent.state.changed", "seq": 42,
 "ts": "2026-04-21T10:00:00Z", "session_id": "sess-...",
 "agent_id": "backend", "from": "IDLE", "to": "WORKING", ...}
```

Two divergences from the frozen schema doc:

1. **Envelope:** flat fields vs. `{..., v, data: {...}}`.
2. **State literal case:** pydantic requires `IDLE|WORKING|BLOCKED|COMPLETED`, the doc shows lowercase.

## Why P1 is not fixing this unilaterally

Per `CLAUDE.md` §Schema lock (G1):

> Once Gate G1 in docs/PLAN.md passes, docs/WEBSOCKET_SCHEMA.md is frozen.
> Schema changes after that require an explicit P1+P2 sync. Do not
> unilaterally edit mesh/schemas/events.py.

P2's overlay consumes the v1.0 envelope already. Flipping pydantic to match
without coordinating could break Abhi's client parser mid-build.

## Decision needed from P2

Option A — adopt the frozen doc (enveloped v1.0, lowercase states):
- P1 rewrites `mesh/schemas/events.py` to emit `{event, v, seq, ts, session_id, data: {...}}`.
- `mesh/mock_events.jsonl` is regenerated in the new shape.
- P1's bus tee + live session events become drop-in for P2.

Option B — amend the schema doc to flat (uppercase states):
- `docs/WEBSOCKET_SCHEMA.md` updated to match pydantic today.
- P2 updates the overlay reducer to read flat fields.

Option C — both (flat envelope at protocol layer; data stays flat inside).
Probably not worth it; either A or B keeps the parser simple.

## Recommendation from P1

**Option A.** The frozen doc is the contract; pydantic drifted. A discriminated
union over the `data` subtree is straightforward with pydantic v2. P1 can
turn it around in one commit once P2 confirms.

## How to unblock

Reply on this file (edit + commit) or ping on Discord. Once P2 signs off I'll
open the follow-up PR with the pydantic + mock_events + tests update, and
this file can be deleted.
