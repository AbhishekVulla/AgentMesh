# AgentMesh — MVP Architecture

> This is the trimmed, hackathon-scoped architecture. For the full spec (coordinator LLM arbitration, auto-split, agent adapters for Claude Code / Codex / Gemini / Ollama, achievements, replay, etc.), see the team's internal `AgentMesh_System_Architecture.md`. The full spec is a 16-week build plan; this document defines the 4-day subset we are shipping.

## 1. Principles

Three, unchanged from the full spec:

1. **File as interface.** All communication is JSON on disk.
2. **Minimum viable context.** Only the relevant dot-paths cross agent boundaries.
3. **Sidecar mediation.** Major agents write their dictionary; Mini Agents handle the protocol.

## 2. Actors (MVP)

| Actor | Role | Count | State |
|---|---|---|---|
| Major Agent | Produces dictionary mutations (in demo: scripted Python) | 3 | Stateless — all state lives in its dictionary file |
| Mini Agent | Sidecar: owns `context.json`, `summary.json`, `input.json`, watches `dictionary.json`, diffs, routes, resolves conflicts | 1 per major agent | Stateful (file-backed) |
| Dictionary Store | Nested JSON, dot-path addressable, versioned | 1 per agent | Persistent (JSON on disk) |
| WebSocket Event Bus | Broadcasts protocol events to the visualizer | 1 per session | Ephemeral |
| Visualizer | VS Code extension: sidebar overlay webview (MVP). Optional pixel-agents JSONL shim (stretch). | 1 | Consumes only |

**Cut from full spec:** Coordinator process, heartbeat health monitor, archive subsystem.

## 3. The three-file system (per agent)

Each agent's directory `.agentmesh/agents/{agent_id}/` contains:

```
dictionary.json     # The agent's work product (what it has "written")
context.json        # Persistent: own state summary + subscribed keys from other agents
summary.json        # Short, human- and agent-readable status
input.json          # Queue of incoming messages from other agents
```

### `dictionary.json`

Nested, dot-path addressable, versioned:

```json
{
  "_meta": {
    "agent_id": "backend",
    "version": 3,
    "updated_at": "2026-04-21T10:30:00Z"
  },
  "backend": {
    "routes": {
      "/api/users": {
        "method": "GET",
        "auth_required": true
      }
    },
    "models": {
      "User": { "fields": { "id": "int", "email": "string" } }
    }
  }
}
```

### `summary.json`

```json
{
  "agent_id": "backend",
  "status": "active",
  "current_task": "Adding auth to /api/users",
  "exposes": ["routes./api/users", "models.User"],
  "consumes": ["database.schema.users"]
}
```

### `input.json`

Append-only queue; Mini Agent drains after processing:

```json
{
  "queue": [
    {
      "id": "msg-20260421-frontend-001",
      "from": "frontend",
      "timestamp": "2026-04-21T10:30:15Z",
      "type": "state_update",
      "priority": "normal",
      "scope": "frontend.api_calls./api/users",
      "diff": { "frontend.api_calls./api/users.headers": { "old": {}, "new": {"Authorization": "Bearer ..."} } },
      "summary": "Frontend added Authorization header to /api/users call"
    }
  ]
}
```

## 4. Message flow (end to end)

```
1. Major Agent writes dictionary.json (scripted timeline in demo)
2. Mini Agent's file watcher (watchdog, 100ms debounce) detects change
3. Diff Engine computes path-aware diff vs. previous version
4. Router reads dependency_map.yaml:
      backend:
        routes.*: [frontend]
        models.*: [database]
   and selects targets for each changed path
5. Message Constructor packages {id, from, to, scope, diff, summary}
6. Atomic write to target's input.json (tempfile + os.replace)
7. Target's Mini Agent reads input.json
8. Conflict Detector compares incoming scope against target's own dictionary
9. If conflict: look up priority table for that path, apply winner, log loser
   If no conflict: update context.json.external_state[sender]
10. Regenerate summary.json if any depth-2 key changed
11. Broadcast events on WebSocket at each step (see WEBSOCKET_SCHEMA.md)
```

**Every step is deterministic. No LLM involvement.**

## 5. Directory layout at runtime

```
project-root/
└── .agentmesh/
    ├── dependency_map.yaml
    ├── agents/
    │   ├── backend/
    │   │   ├── dictionary.json
    │   │   ├── dictionary.history.jsonl     # append-only log
    │   │   ├── context.json
    │   │   ├── summary.json
    │   │   └── input.json
    │   ├── frontend/
    │   │   └── ...
    │   └── database/
    │       └── ...
    └── events/
        └── session.jsonl                    # all WebSocket events tee'd here
```

## 6. Dependency map

```yaml
# .agentmesh/dependency_map.yaml

backend:
  publishes:
    routes.*: { notify: [frontend], tier: L2 }
    models.*: { notify: [database], tier: L2 }
    auth.*:   { notify: [frontend], tier: L2, priority: high }
  subscribes:
    database.schema.*: L2

frontend:
  publishes:
    api_calls.*: { notify: [backend], tier: L2 }
  subscribes:
    backend.routes.*: L2
    backend.auth.*:   L2

database:
  publishes:
    schema.*: { notify: [backend], tier: L2 }
  subscribes:
    backend.models.*: L2
```

## 7. Conflict resolution (MVP)

Deterministic priority table only. No LLM.

```yaml
# Priority per domain — higher index wins
route_auth_changes:
  winners: [backend, frontend, database]   # backend wins
schema_changes:
  winners: [database, backend, frontend]   # database wins
component_changes:
  winners: [frontend, backend, database]   # frontend wins
```

When `Conflict Detector` flags an incoming diff, it looks up the key pattern in the priority table, picks the winner, writes the resolution to the loser's `input.json` as a `response` message with `correlation_id` pointing to the original conflict, and broadcasts `conflict.detected` + `conflict.resolved` on the WebSocket.

**Full spec has coordinator-escalate + LLM arbitration. We cut both.**

## 8. Component responsibilities

```
┌──────────────────────── Mini Agent (Python) ────────────────────────┐
│                                                                      │
│  File Watcher          Diff Engine         Router                    │
│   (watchdog)            (path-aware)        (dependency_map.yaml)     │
│       │                     │                    │                    │
│       v                     v                    v                    │
│  Summarizer            Conflict Detector    Message Constructor       │
│   (template only)       (priority table)    (pydantic validated)      │
│       │                     │                    │                    │
│       └─────────────────────┼────────────────────┘                    │
│                             v                                         │
│                      Input Processor                                  │
│                      (validate, dedupe, prioritize)                   │
│                             │                                         │
│                             v                                         │
│                      WebSocket Emitter                                │
│                      (ws://localhost:9900)                            │
└──────────────────────────────────────────────────────────────────────┘
```

## 9. Atomic file writes

Every dictionary write uses write-to-temp-then-rename:

```python
import os, tempfile, json
def atomic_write_json(path, data):
    dir_ = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise
```

Rationale: Windows 11 does not POSIX-rename atomically on older APIs but `os.replace` works. Prevents the file watcher from reading half-written JSON.

## 10. What is intentionally NOT here

These appear in the full architecture doc and are **cut from the MVP**:

- Version vectors (just use monotonic integer version + timestamp)
- SHA-256 checksums per file (skip integrity layer)
- Zlib compression for large values (out of scope for 90s demo)
- Tiered detail system L1/L2/L3 (use L2 only — structured summary)
- Heartbeat process (agents are ephemeral; session ends, they exit)
- Coordinator process (conflicts resolved peer-to-peer via priority table)
- Archive / decisions_log pruning (demo runs for 90s, no growth pressure)
- `am` CLI, auto-split, guided task planner
- LLM-assisted summarization (template-only)

## 11. Tech stack

- **Python 3.11+**
- `watchdog` — file system watching
- `websockets` — async WebSocket server
- `pydantic v2` — message / event schema validation
- `pyyaml` — `dependency_map.yaml` loader
- `pytest` — tests
- No web framework — pure `websockets` library

## 12. References

- [WEBSOCKET_SCHEMA.md](WEBSOCKET_SCHEMA.md) — event contract
- [DEMO_SCENARIO.md](DEMO_SCENARIO.md) — 90-second scenario
- Full spec: team's internal `AgentMesh_System_Architecture.md` (not committed to this repo)
