# AgentMesh — Demo Scenario

> The 90-second choreographed scenario used for the pitch video. Deterministic, reproducible, no network calls, no LLMs.

## Setup

Three scripted Python "major agents" drive dictionary mutations on a timeline:

- `backend` — simulates a Claude-Code-style backend session
- `frontend` — simulates a Cursor/Gemini-style frontend session
- `database` — simulates an Ollama/DB session

Each one is a dumb Python script that `sleep()`s between scripted mutations. They are **not** LLMs. This is the point — the protocol works without any LLM involvement, which is the "not a prompt wrapper" evidence.

Each scripted agent owns an `.agentmesh/agents/{id}/dictionary.json`. Its Mini Agent sidecar watches the file, diffs it, routes changes, and handles its incoming `input.json`.

## Timeline (T+seconds)

| T | Who | Action | Dictionary mutation | Routed to | WebSocket events |
|---|---|---|---|---|---|
| 0.0 | — | Session starts | — | — | `mesh.session.started` |
| 1.0 | database | State → working | — | — | `agent.state.changed` |
| 2.0 | database | Defines users table schema | `database.schema.users.columns = [id, name, email, created_at]` | backend | `dict.mutated`, `message.sent` |
| 4.0 | backend | State → working | — | — | `agent.state.changed` |
| 5.0 | — | Backend's Mini Agent processes database's message | — | — | `message.delivered` |
| 6.0 | backend | Aligns User model with schema | `backend.models.User.fields = {id: int, name: string, email: string, created_at: datetime}` | database | `dict.mutated`, `message.sent` |
| 8.0 | backend | Adds GET `/api/users` route, auth-less initially | `backend.routes./api/users = {method: GET, auth_required: false}` | frontend | `dict.mutated`, `message.sent` |
| 10.0 | frontend | State → working | — | — | `agent.state.changed` |
| 11.0 | — | Frontend's Mini Agent processes backend's message | — | — | `message.delivered` |
| 12.0 | frontend | Adds API call without Authorization header | `frontend.api_calls./api/users = {method: GET, headers: {}}` | backend | `dict.mutated`, `message.sent` |
| 15.0 | backend | Security promote: route now requires auth | `backend.routes./api/users.auth_required = true` | frontend | `dict.mutated`, `message.sent` |
| 17.0 | — | **Frontend's Mini Agent detects conflict** on `backend.routes./api/users.auth_required` (was implicitly false, now true, but frontend's api_call has no auth header) | — | — | `conflict.detected` |
| 18.0 | — | Priority table: `route_auth_changes` → backend wins over frontend | Resolution written to frontend's `input.json` as `response` with `correlation_id` | frontend | `conflict.resolved` |
| 20.0 | frontend | Applies resolution: adds auth header | `frontend.api_calls./api/users.headers = {Authorization: "Bearer {{token}}"}` | backend | `dict.mutated`, `message.sent` |
| 22.0 | backend | Acknowledges (state → completed) | — | — | `agent.state.changed`, `message.delivered` |
| 24.0 | database | State → completed | — | — | `agent.state.changed` |
| 25.0 | frontend | State → completed | — | — | `agent.state.changed` |
| 26.0 | — | Session ends | — | — | `mesh.session.ended` |

Throughout, `metrics.tick` emits at 1 Hz.

## Final state

After the scenario runs, the three `dictionary.json` files should contain:

**`.agentmesh/agents/database/dictionary.json`**
```json
{
  "_meta": { "agent_id": "database", "version": 1 },
  "database": {
    "schema": {
      "users": {
        "columns": ["id", "name", "email", "created_at"]
      }
    }
  }
}
```

**`.agentmesh/agents/backend/dictionary.json`**
```json
{
  "_meta": { "agent_id": "backend", "version": 3 },
  "backend": {
    "models": {
      "User": { "fields": { "id": "int", "name": "string", "email": "string", "created_at": "datetime" } }
    },
    "routes": {
      "/api/users": { "method": "GET", "auth_required": true }
    }
  }
}
```

**`.agentmesh/agents/frontend/dictionary.json`**
```json
{
  "_meta": { "agent_id": "frontend", "version": 2 },
  "frontend": {
    "api_calls": {
      "/api/users": {
        "method": "GET",
        "headers": { "Authorization": "Bearer {{token}}" }
      }
    }
  }
}
```

## What the viewer sees (2-minute video narration)

The AgentMesh overlay (sidebar webview) is the hero. If the pixel-agents shim stretch landed, it shows in the bottom panel as a bonus — referred to as "and here's the pixel-office view for fun" rather than a central element.

**Hook (0:00-0:10):** "What if agents could coordinate without an orchestrator — without shared memory — without retrofitting human tools onto AI workflows?"

**Launch (0:10-0:20):** Open VS Code. Sidebar: AgentMesh overlay opens, shows three agent cards (backend, frontend, database) all IDLE, empty dictionary trees beneath each.

**Work phase (0:20-0:50):** Database card transitions to WORKING, current task "Adding users table schema" appears. Tree populates with `schema.users.columns`. A courier orb animates from database card to backend card. Backend card: badge flips to WORKING, tree populates with `models.User` and `routes./api/users`. Frontend does the same.

**Conflict (0:50-1:05):** Backend sets `auth_required: true`. **Conflict panel slides in**, shows side-by-side: backend value `true` with reason "Security — protect PII", frontend value `false` with reason "Built call without auth header". Narrator: "The priority table resolves this in under 50 milliseconds — no LLM call, no orchestrator, deterministic." Panel flashes green, `winner: backend` banner appears, frontend's api_calls tree updates to include the Authorization header.

**Evidence (1:05-1:30):** "Every message you saw was path-filtered. The metrics bar shows 68% fewer bytes exchanged versus a naive full-context baseline. And the whole session — protocol included — runs with zero LLM calls." Terminal overlay shows `env | grep -iE 'anthropic|openai'` returning nothing, session still completes successfully.

**Close (1:30-2:00):** "AgentMesh is infrastructure for AI-to-AI coordination. Swap the scripted agents for Claude Code, Codex, or any model — the protocol doesn't care. The code is public." GitHub link on screen.

**Stretch (only if shim landed):** During the work phase, cut briefly to the pixel-agents bottom panel showing three characters moving at desks — reinforces "this is real coordination between identifiable agents" without distracting from the overlay.

## Determinism requirements (for the integration test)

The scenario MUST produce the same event `seq` values across runs (timestamps may vary). The test in `mesh/tests/test_scenario.py`:

1. Runs `demo/run_scenario.py` with `SESSION_ID=test-fixture-01`
2. Reads `.agentmesh/events/session.jsonl`
3. Asserts the ordered list of `(seq, event)` tuples matches a golden file
4. Asserts final dictionary states match the three JSON blobs above exactly
5. Asserts `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` env vars are unset during the run (proves no LLM calls)

## Why this scenario (judging rationale)

- **Challenge-Solution fit:** Shows *actual* AI-to-AI coordination — dictionary mutations propagating across agents with zero orchestrator and zero LLM in the loop.
- **Technological execution:** Conflict → priority-table resolution → follow-up message is all real protocol, visible in code.
- **Product thinking:** Side-by-side (characters + data) tells two complementary stories in one screen.
- **Originality:** The scripted-agent framing is the "gotcha" — judges who ask "but where's the LLM?" are the ones who understand the value proposition.
- **Evidence of real demand:** Pain points (orchestrator bottleneck, context explosion, retrofit tax) are grounded in the team's ideation transcript.
