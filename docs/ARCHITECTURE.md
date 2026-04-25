# AgentMesh — Architecture

> This document describes the v0.1 protocol architecture. Features deferred from v0.1 (coordinator LLM arbitration, tiered L1/L2/L3 detail system, cross-agent version vectors, Task Definition workflow, agent adapters, replay) are listed in [PRD.md](PRD.md) §4.2.

## 1. Principles

1. **File as interface.** All communication is JSON on disk.
2. **Minimum viable context.** Only the relevant dot-paths cross agent boundaries.
3. **Sidecar mediation.** Major agents write their dictionary; Mini Agents handle the protocol.

## 2. Actors

| Actor | Role | Count | State |
|---|---|---|---|
| Major Agent | Produces dictionary mutations (in reference scenario: scripted Python) | N | Stateless — all state lives in its dictionary file |
| Mini Agent | Sidecar: owns `context.json`, `summary.json`, `input.json`, watches `dictionary.json`, diffs, routes, resolves conflicts | 1 per major agent | Stateful (file-backed) |
| Dictionary Store | Nested JSON, dot-path addressable, versioned | 1 per agent | Persistent (JSON on disk) |
| WebSocket Event Bus | Broadcasts protocol events to the visualizer | 1 per session | Ephemeral |
| Visualizer | VS Code extension: sidebar overlay webview (MVP). Optional pixel-agents JSONL shim (stretch). | 1 | Consumes only |

**Not in v0.1:** Coordinator process, heartbeat health monitor, archive subsystem.

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

### 6.1 Pattern-matching semantics

All patterns in `publishes` / `subscribes` use **path-prefix matching with an optional `.*` suffix for readability**:

- `routes.*` — matches `routes./api/users`, `routes./api/users.method`, `routes./api/users.auth_required`, and any other descendant of `routes.`
- `routes` (no suffix) — equivalent to `routes.*`
- `routes./api/users` — matches that exact path AND all its descendants (prefix match)
- `*.method` — NOT supported in v0.1 (middle/suffix wildcards require a richer matcher)

Implementation hint: strip any trailing `.*` from the pattern, then test if `change.path == pattern` OR `change.path.startswith(pattern + '.')`. That's it.

**Scoping to a publishing agent:** when frontend declares `subscribes: backend.routes.*`, the pattern is `routes.*` within the backend agent's dictionary namespace. The router consults the publishing agent's `publishes` entries first, then cross-references against each subscriber's `subscribes` list.

## 7. Conflict resolution

Deterministic, dual-mechanism. No LLM.

### 7.1 Two kinds of conflict

**Type A — Direct path conflict.** Two agents wrote to the same exact dot-path with different values within the same version window. Cheap to detect via version-vector comparison. Example: both backend and codex-test set `backend.routes./api/users.auth_required` to different values.

**Type B — Semantic cross-reference conflict.** Two agents wrote to *different* dot-paths, but a declared rule says those paths must be kept consistent. Example: backend sets `backend.routes./api/users.auth_required = true`, but frontend's `frontend.api_calls./api/users.headers` has no `Authorization` entry. The paths don't overlap; the rule does.

The reference scenario exercises both Type A (via path collisions from routed messages) and Type B (via two declared rules).

### 7.2 Type A detection (generic)

For each incoming `state_update` message, compare its diff paths against the receiver's own dictionary. If any path in the diff already exists in the receiver's dict with a different value, flag a Type A conflict.

### 7.3 Type B detection (rules)

Hardcoded in `mesh/conflict.py` as a list of rule objects (Python dataclasses). Each rule has:

- `id`: string — e.g. `auth_required_on_route`
- `trigger`: `{agent, path_glob, value_predicate}` — when agent X changes a path matching this glob to a value satisfying this predicate
- `required_peer`: `{agent, path_template}` — in agent Y's dict, a path interpolated from the trigger match's wildcards must exist (and optionally be truthy)
- `winner`: which agent wins
- `resolution_message`: template string for the follow-up message to the loser

Example for the demo:

```python
ConflictRule(
    id="auth_required_on_route",
    trigger={
        "agent": "backend",
        "path_glob": "routes.{route}.auth_required",
        "value_predicate": lambda v: v is True,
    },
    required_peer={
        "agent": "frontend",
        "path_template": "api_calls.{route}.headers.Authorization",
        "must_exist": True,
    },
    winner="backend",
    resolution_message=(
        "Backend route {route} now requires authentication. "
        "Please add an Authorization header to your api_calls.{route}."
    ),
)
```

When backend's Mini Agent publishes a `routes.*.auth_required` diff, the Router also evaluates Type B rules where backend is the trigger. If frontend is the required_peer and the `Authorization` path is missing in frontend's dict, the Router emits a `conflict.detected` event (with both sides' state) and immediately writes a `response`-type message to frontend's `input.json` containing the interpolated `resolution_message`. Frontend's Mini Agent processes it on its next input-queue read and the scripted agent acts on it.

### 7.4 Priority table

Type A resolution falls back to a simple priority map in `mesh/conflict.py`:

```python
PRIORITY_BY_PATH_PREFIX = {
    "routes":     ["backend", "frontend", "database"],
    "schema":     ["database", "backend", "frontend"],
    "api_calls":  ["frontend", "backend", "database"],
    "auth":       ["backend", "frontend", "database"],
}
```

For a Type A conflict on path `backend.routes./api/users.auth_required`, match the key by its second segment (`routes` in this case, since first is agent-id namespace), look up the ordered list, pick the agent closest to the head that is among the conflicting parties. Exact, deterministic, zero LLM.

**Coordinator-escalate with LLM arbitration is deferred to a later version.**

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

## 10. What is intentionally NOT in v0.1

Deferred features (see [PRD.md](PRD.md) §4.2 for the full list):

- Cross-agent version vectors (v0.1 uses monotonic integer version + timestamp)
- SHA-256 checksums per file (no integrity layer in v0.1)
- Tiered detail system L1/L2/L3 (v0.1 transmits full diffs)
- Heartbeat process (agents are ephemeral; session ends, they exit)
- Coordinator process (conflicts resolved peer-to-peer via priority table + declared rules)
- Archive / decisions_log pruning
- Task Definition Document / agent-split workflow / `am` CLI
- LLM-assisted summarization (summaries are written by the scripted drivers in v0.1)

## 11. Tech stack

- **Python 3.11+**
- `watchdog` — file system watching
- `websockets` — async WebSocket server
- `pydantic v2` — message / event schema validation
- `pyyaml` — `dependency_map.yaml` loader
- `pytest` — tests
- No web framework — pure `websockets` library

## 12. Runtime orchestration (`demo/run_scenario.py`)

Two processes: the protocol bus and the scenario driver.

```
Terminal 1: python -m mesh.run --config demo/config.yaml
├── asyncio event loop
│   ├── mesh.ws_server     — serves WebSocket on :9900
│   └── mesh.MiniAgent × N — one per agent in config.yaml; each watches
│                            its agent_dir/{dictionary,summary,input}.json
└── tees every event to .agentmesh/events/session.jsonl

Terminal 2: python -m demo.run_scenario
└── single-process driver — calls dict_store.set() against each agent's
    dictionary.json on a timeline. Mini Agents (in Terminal 1) detect
    the mtime change, diff, route, and emit events.
```

### 12.1 Startup sequence

1. Operator wipes `.agentmesh/` (optional, for clean runs).
2. **Terminal 1:** `python -m mesh.run --config demo/config.yaml --duration 180`
   - Creates `.agentmesh/agents/{id}/` for each agent in the config (six in the reference scenario), with empty `dictionary.json`, `summary.json`, `input.json`.
   - Loads `demo/dependency_map.yaml` + `demo/priority_table.yaml`.
   - Starts the WebSocket server, broadcasts `mesh.session.started`.
   - Starts a `MiniAgent` instance per agent, each watching its directory.
3. **Terminal 2:** `python -m demo.run_scenario`
   - Single-threaded Python script that opens a `DictStore` for each agent and calls `store.set(dotpath, value)` on a timeline (with `time.sleep` between writes).
   - Each `set` triggers `dict_store.atomic_write_json` → file mtime changes → Mini Agent in Terminal 1 detects + processes.
4. Mini Agents emit `dict.mutated` → router fans out → `message.sent` → target Mini Agent's `drain_input` → `message.delivered` → `_apply_incoming` runs Type A detection → `_evaluate_type_b` runs Type B rules.
5. Conflicts produce `conflict.detected` + `conflict.resolved` events with priority-table or rule-based winners.
6. After ~50s the scenario script exits. Terminal 1 keeps running until `--duration` elapses (or Ctrl+C), then broadcasts `mesh.session.ended`.

### 12.2 State-change signal convention

Scripted drivers flip an agent's state by writing a small JSON record to `.agentmesh/agents/{id}/summary.json` (e.g., `{"state": "WORKING", "current_task": "..."}`). The session loop polls `summary.json` mtime, detects the change, and broadcasts `agent.state.changed` over the WebSocket bus. States: `IDLE | WORKING | BLOCKED | COMPLETED`.

### 12.3 Cross-process coordination

- Mini Agents (Terminal 1) and the scenario driver (Terminal 2) communicate **only through the filesystem** — no IPC, no sockets between them.
- `dict_store.atomic_write_json` (`tempfile.mkstemp` + `os.replace`) ensures Mini Agents never read a half-written file.
- The session loop polls each agent's `dictionary.json` and `summary.json` mtime once per tick; changes trigger handlers.

### 12.4 Reproducibility

Every session writes its full event log to `.agentmesh/events/session.jsonl`. Two runs of the reference scenario produce the same ordered list of event types (timestamps and `seq` values vary by OS scheduling). Unit tests under `mesh/tests/` cover the conflict-rule evaluation logic and schema round-trip; integration testing of the full scenario is done by inspecting the tee'd JSONL.

## 13. References

- [WEBSOCKET_SCHEMA.md](WEBSOCKET_SCHEMA.md) — event contract
- [DEMO_SCENARIO.md](DEMO_SCENARIO.md) — scenario timeline
