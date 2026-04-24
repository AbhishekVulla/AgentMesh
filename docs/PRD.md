# AgentMesh — Product Specification

> Current state: v0.1. Protocol + visualization layer shipped. Reference scenario runs deterministically; the event bus, dictionary store, diff engine, router, dual-mechanism conflict resolver, VS Code extension, and browser overlay are all working code.

## 1. Problem

Most software infrastructure today assumes humans are the primary operators. Agentic systems increasingly need to coordinate with other agents, tools, and environments directly. The question: how do you build infrastructure *designed for* AI-to-AI interaction, rather than retrofitting human-centered software for agent workflows?

Current multi-agent setups fail in three concrete ways:

1. **Orchestrator bottleneck.** Every agent-to-agent message gets summarized by a central LLM orchestrator, losing 20-30% of the semantic signal each hop. Inter-agent decisions degrade like a telephone game.
2. **Context window explosion.** Passing full context between N agents is O(N) per message and burns tokens fast.
3. **Retrofit tax.** Chat UIs, IDEs, and ticket systems are built for humans; using them as the coordination layer between agents adds latency, serialization overhead, and format-mismatch errors that LLMs must waste tokens to paper over.

## 2. What AgentMesh is

A file-based, protocol-driven communication layer that sits between any set of AI agents. Agents don't talk directly. Each major agent is paired with a **Mini Agent sidecar** — a small Python process that owns three files (`context.json`, `summary.json`, `input.json`) and a versioned dictionary store.

Core properties:

- **File-as-interface.** No sockets, no DB, no MQ between agents. JSON files on disk. Anything that can read/write JSON can participate.
- **Minimum viable context.** When agent A changes `backend.routes./api/users`, agent B receives only that dot-path and its diff — not the whole backend state. Dependency maps declare who cares about what.
- **Deterministic hot path.** Diffing, routing, and priority-based conflict resolution have zero LLM calls. The protocol runs offline, reproducibly, and cheaply.
- **Sidecar mediation.** Major agents focus on their coding task; Mini Agents handle all protocol operations.

## 3. Target users

Not end-users. Infrastructure consumers:

1. **Orchestrator authors** (LangGraph, AutoGen, CrewAI, custom) who want a standard inter-agent protocol instead of hand-rolled JSON.
2. **IDE authors** adding multi-agent coordination (Cursor, Windsurf, Zed) who need a non-proprietary wire format.
3. **Individual developers** running parallel agents locally who want deterministic coordination without a heavy orchestrator.
4. **Multi-agent systems researchers** who need a reproducible, inspectable protocol to measure coordination quality.

## 4. Scope

### 4.1 In scope (v0.1 — shipped)

**Protocol:**

1. Mini Agent sidecar process (Python 3.11+)
2. Dictionary store with dot-path addressing, atomic writes, versioned history
3. Path-aware diff engine
4. Dependency-map driven router
5. Dual-mechanism conflict resolver (Type A direct path collision + Type B semantic cross-reference rules) — deterministic lookup table, no LLM
6. WebSocket event broadcaster on `ws://localhost:9900`
7. Scripted 6-agent reference scenario (`demo/run_scenario.py`) — ~50s deterministic run producing 24 routed messages and two Type B conflict resolutions
8. End-to-end tests covering conflict rule evaluation and schema round-trip

**Visualization:**

1. VS Code extension (TypeScript + webview, sidebar activity-bar view)
2. WebSocket client with reconnect backoff
3. Browser overlay (pixel-office aesthetic) rendering live sessions:
   - Agent cards with state badges (IDLE/WORKING/BLOCKED/COMPLETED) and current-task text
   - Dictionary store tree per agent, live-updating on `dict.mutated`
   - Message flow animations on `message.sent`/`message.delivered`
   - Conflict panel on `conflict.detected`, clears on `conflict.resolved`
   - Metrics strip: messages, conflicts, bytes exchanged, estimated token-savings %
4. Overlay runs standalone — no dependency on pixel-agents or any third-party visualizer

### 4.2 Not in v0.1

Features in the broader protocol vision but deferred:

- LLM-based coordinator process for semantic conflict escalation (current resolver is priority-table only)
- Tiered L1/L2/L3 detail system (current router transmits full diffs)
- Cross-agent version vectors (current conflict detection uses path collision + declared rules)
- Version-vector-based catch-up for missed messages
- Task Definition Document / agent-split workflow
- Quality-review phase + completion report
- Agent adapters (CLI / API / local) for translating real LLM outputs into dictionary mutations
- Timeline scrubber, session replay, standalone web viewer
- Provider-specific integrations beyond the reference scripted drivers

## 5. Acceptance criteria

**Protocol:**

- [x] `pytest mesh/tests/` passes
- [x] `python -m mesh.run --config demo/config.yaml` starts a WebSocket server listening on port 9900
- [x] `python -m demo.run_scenario` completes in ~50 seconds and emits the event sequence defined in [DEMO_SCENARIO.md](DEMO_SCENARIO.md)
- [x] Six `dictionary.json` files exist under `.agentmesh/agents/{orchestrator,researcher,tests,formatter,reviewer,agent-6}/` after a run
- [x] Both Type B conflicts (`breaking_change_needs_migration_test` and `security_review_needs_lint_check`) detect and resolve, visible in the tee'd `session.jsonl`
- [x] No LLM API calls in the hot path (verifiable by running with `ANTHROPIC_API_KEY=` and `OPENAI_API_KEY=` unset — protocol still works end-to-end)

**Visualization:**

- [x] VS Code extension loads cleanly in an Extension Development Host on Windows 11
- [x] Sidebar webview connects to `ws://localhost:9900` and renders live events
- [x] Six agent cards render with state badges and current-task text
- [x] Dictionary tree updates on every `dict.mutated` event
- [x] Courier animations play on `message.sent`
- [x] Conflict panel opens on `conflict.detected` and clears on `conflict.resolved`
- [x] Metrics bar increments from `metrics.tick` events

## 6. Non-goals

- Not an orchestrator. Orchestrators consume AgentMesh; they don't replace it.
- Not a model router. Model selection is upstream.
- Not a shared workspace. Agents don't share memory — they share structured messages.
- Not a compiler or code generator. The protocol's "work product" is coordinated dictionary state, not running software.

## 7. Related docs

- [ARCHITECTURE.md](ARCHITECTURE.md) — protocol architecture
- [WEBSOCKET_SCHEMA.md](WEBSOCKET_SCHEMA.md) — event contract
- [DEMO_SCENARIO.md](DEMO_SCENARIO.md) — reference scenario timeline
