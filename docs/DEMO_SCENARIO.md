# AgentMesh — Reference Scenario

> The ~50-second choreographed scenario used to exercise every protocol primitive. Deterministic, reproducible, no network calls, no LLMs.

## Setup

Six scripted Python drivers mutate dictionary files on a timeline:

- `orchestrator` — coordinates the work, emits a high-level plan
- `researcher` — drafts the `/api/users` API contract
- `tests` — authors test cases including migration tests
- `formatter` — configures lint rules (PEP8 + security checks)
- `reviewer` — approves and flags security requirements
- `agent-6` — pins dependencies (bcrypt version)

Each driver is a Python function that `sleep()`s between scripted dictionary writes. They are **not** LLMs. This is the point — the protocol works without any LLM involvement, which is the core technical claim.

Each scripted driver owns an `.agentmesh/agents/{id}/dictionary.json`. Its Mini Agent sidecar watches the file, diffs it, routes changes per [`demo/dependency_map.yaml`](../demo/dependency_map.yaml), and handles its incoming `input.json`.

## Timeline (T+seconds)

| T | Who | Action | Dictionary mutation | Routed to | WebSocket events |
|---|---|---|---|---|---|
| 0.0 | — | Session starts | — | — | `mesh.session.started` |
| 2.0 | orchestrator | State → WORKING | — | — | `agent.state.changed` |
| 3.5 | orchestrator | Declares the feature and subtasks | `orchestrator.plan.feature = "user-auth"`, `orchestrator.plan.subtasks = [...]` | researcher, agent-6 | `dict.mutated`, 2× `message.sent` |
| 7.0 | researcher, agent-6 | State → WORKING | — | — | 2× `agent.state.changed` |
| 9.0 | researcher | Publishes /api/users contract | `researcher.contracts./api/users.fields = {...}` | tests, formatter | `dict.mutated`, 2× `message.sent` |
| 11.0 | tests, formatter | State → WORKING | — | — | 2× `agent.state.changed` |
| 13.0 | agent-6 | Pins dependency | `agent-6.dependencies.bcrypt = {version: "4.0.1", checksum: ...}` | reviewer, orchestrator | `dict.mutated`, 2× `message.sent` |
| 15.0 | tests | Publishes happy-path case | `tests.cases./api/users.happy_path = {...}` | reviewer | `dict.mutated`, `message.sent` |
| 17.0 | formatter | Publishes initial style | `formatter.lint_rules./api/users.style = "PEP8"` | reviewer | `dict.mutated`, `message.sent` |
| 19.0 | reviewer | State → WORKING | — | — | `agent.state.changed` |
| 21.0 | researcher | **Flags contract as breaking change** | `researcher.contracts./api/users.breaking_change = true` | — | `dict.mutated` |
| ~21.1 | — | **Conflict #1 fires** (Type B rule `breaking_change_needs_migration_test`): tests lacks `cases./api/users.migration_test` | — | — | `conflict.detected`, `conflict.resolved` (winner: researcher), `message.sent` (resolution to tests) |
| 23.0 | tests | State → BLOCKED, applies resolution | `tests.cases./api/users.migration_test = {...}` | reviewer | `agent.state.changed`, `dict.mutated`, `message.sent` |
| 26.5 | tests | State → WORKING | — | — | `agent.state.changed` |
| 28.0 | reviewer | Drops initial approval | `reviewer.approvals./api/users.initial = true` | orchestrator, formatter | `dict.mutated`, 2× `message.sent` |
| 30.0 | reviewer | **Demands security coverage** | `reviewer.approvals./api/users.security_required = true` | — | `dict.mutated` |
| ~30.1 | — | **Conflict #2 fires** (Type B rule `security_review_needs_lint_check`): formatter lacks `lint_rules./api/users.security_check` | — | — | `conflict.detected`, `conflict.resolved` (winner: reviewer), `message.sent` (resolution to formatter) |
| 33.0 | formatter | State → BLOCKED, applies resolution | `formatter.lint_rules./api/users.security_check = true` | reviewer | `agent.state.changed`, `dict.mutated`, `message.sent` |
| 36.0 | formatter | State → WORKING | — | — | `agent.state.changed` |
| 37.5 | reviewer | Signs off | `reviewer.approvals./api/users.approved = true` | orchestrator, formatter | `dict.mutated`, 2× `message.sent` |
| 39.0 | orchestrator | Merging | `orchestrator.plan.status = "merged"` | researcher, agent-6 | `dict.mutated`, 2× `message.sent` |
| 42-47 | all | State → COMPLETED (staggered) | — | — | 6× `agent.state.changed` |
| ~50 | — | Session ends | — | — | `mesh.session.ended` |

Throughout, `metrics.tick` emits at ~1 Hz.

## Expected totals after a clean run

- 6 agents registered
- ~13 `dict.mutated` events
- 24 `message.sent` / 24 `message.delivered` (routed via dependency map + 2 conflict-resolution messages)
- 2 `conflict.detected` / 2 `conflict.resolved` (both Type B rules)
- ~16 `agent.state.changed` events
- Session tee'd to `.agentmesh/events/session.jsonl` for replay

## What the live view shows

The VS Code sidebar and browser overlay render the session in real time:

- Six agent cards oscillating through IDLE → WORKING → BLOCKED → COMPLETED as scripted drivers flip their `summary.json` state
- Dictionary trees growing under each agent card as new paths are written
- Courier animations from source to target agents when messages are routed
- Two conflict cards appearing in sequence: first the breaking-change/migration-test resolution, then the security-required/security-check resolution. Each card slides in on `conflict.detected` and flashes green on `conflict.resolved` with the rule ID and winner.
- Metrics strip counting messages, conflicts, bytes exchanged, and estimated token savings versus a naive full-context baseline

## Determinism requirements

The scenario should produce the same ordered list of event types across runs (timestamps may vary). An integration test can:

1. Run `python -m demo.run_scenario` against a running `mesh.run`
2. Read `.agentmesh/events/session.jsonl`
3. Assert the ordered list of event types matches a golden list
4. Assert per-event-type counts match (2 `conflict.detected`, 2 `conflict.resolved`, 24 `message.sent`, etc.)
5. Assert `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` env vars are unset during the run — proof that no LLM calls happened
