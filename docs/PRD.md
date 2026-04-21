# AgentMesh — Product Requirements (Hackathon Edition)

> Scope: **strAIght up! Hackathon 2026** submission. 4-day build window (Apr 21-25, 2026).
> This document is the product contract for the hackathon MVP. The full system spec lives in the team's internal architecture document; this PRD **deliberately cuts scope** to what is shippable in 4 days.

## 1. Problem

From the challenge statement:

> Most software infrastructure today assumes humans are the primary operators. But agentic systems increasingly need to coordinate with other agents, tools, and environments directly. How might we build infrastructure designed for AI-to-AI interaction, rather than retrofitting human-centered software for agent workflows?

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

## 3. Target users (who this is for)

Not end-users. **Infrastructure consumers:**

1. **Orchestrator authors** (LangGraph, AutoGen, CrewAI, custom) who want a standard inter-agent protocol instead of hand-rolled JSON.
2. **IDE authors** adding multi-agent coordination (Cursor, Windsurf, Zed) who need a non-proprietary wire format.
3. **Individual developers** running parallel agents locally (Claude Code + Cursor + Ollama) who want deterministic coordination without a heavy orchestrator.
4. **Multi-agent systems researchers** who need a reproducible, inspectable protocol to measure coordination quality.

## 4. Hackathon MVP scope

### 4.1 In scope (must ship by Apr 25)

**Backend / protocol (P1 — Ishaan, Claude 20x):**

1. Mini Agent sidecar process (Python 3.11+)
2. Dictionary store with dot-path addressing, atomic writes, SHA-256 integrity
3. Path-aware diff engine
4. Dependency-map driven router
5. Priority-based conflict resolver (deterministic lookup table, no LLM)
6. WebSocket event broadcaster on `ws://localhost:9900`
7. Three scripted demo agents (`demo/backend_agent.py`, `frontend_agent.py`, `database_agent.py`) driving the 90-second scenario
8. One end-to-end integration test that runs the full scenario and asserts the event sequence

**Visualizer (P2 — Abhi, Claude 5x):**

1. VS Code extension scaffold (TypeScript + webview, sidebar activity-bar view)
2. WebSocket client consuming the event stream from `ws://localhost:9900`
3. **AgentMesh overlay webview** (the hero visual) — React panel showing live:
   - **Agent strip**: 3 agent cards (backend / frontend / database) with state badge (IDLE/WORKING/BLOCKED/COMPLETED) and current-task text
   - **Dictionary store tree** per agent (expandable, live-updating on `dict.mutated`)
   - **Message flow**: animated courier orbs traveling between agent cards on `message.sent`/`message.delivered`
   - **Conflict panel**: slides open on `conflict.detected`, shows both values + priority-table reason, clears on `conflict.resolved`
   - **Metrics bar**: messages, conflicts, bytes exchanged, estimated token-savings %
4. The overlay is fully standalone — it renders AgentMesh sessions with zero dependency on pixel-agents

Rationale: after reviewing the actual `pablodelucca/pixel-agents` v1.3.0 source (dual-mode hooks+JSONL session detection, expects real Claude Code transcript format scanned from specific project directories, hardcoded recognized tool names), driving pixel-agents from AgentMesh is a 1-2 day shim project in its own right. The overlay shows the AgentMesh-specific data that pixel-agents can't — dict state, routing, conflicts — so it's the stronger primary visualization anyway.

**Submission deliverables (P3 + P4):**

1. Pitch deck PDF — Problem / Solution / How it works (screenshots) / Ideal users / What's unique
2. Demo video ≤ 2 minutes — posted to YouTube, public link
3. This repo — public at submission time with setup-reproducing README
4. Devpost submission form filled per checklist

### 4.2 Stretch (if ahead of schedule)

- **pixel-agents JSONL shim** — synthetic Claude Code transcript writer so `pablodelucca/pixel-agents` renders our 3 AgentMesh agents as pixel characters in the bottom panel, alongside the sidebar overlay. Requires writing valid Claude Code JSONL to `~/.claude/projects/{workspace-hash}/` with `assistant`-type records containing `tool_use` blocks using recognized tool names (Read/Edit/Write/Bash/Grep/etc.). P2 Day 4 stretch only.
- Coordinator process with LLM-escalation for semantic conflicts (Claude Haiku)
- Real Claude Code as one of the three agents (replaces one scripted agent)
- Session replay (export event log, play back in overlay with a scrubber)
- Token economy counter benchmarked against a real same-task single-context run

### 4.3 Explicitly cut (not shipping)

All of these are in the full spec but **not** part of the hackathon:

- Auto-split, guided task planner, `am plan`/`am split` CLIs
- Full coordinator LLM arbitration (keep priority-table only)
- Checksums / compression / archive / heartbeat health monitoring
- Agent achievements, XP, session scoring
- Timeline scrubber, replay, standalone web app
- Marketplace distribution of the extension
- Support for > 3 agents in a session
- Any actual generated project code — the demo's "work product" is dictionary state, not running software
- pixel-agents fork or source modifications (coexist only)

## 5. Acceptance criteria

A reviewer (or judge) should be able to verify every box:

**Technical correctness:**

- [ ] `pytest mesh/tests/` passes, including the end-to-end scenario test
- [ ] Running `python demo/run_scenario.py` completes in ≤ 120 seconds and emits the event sequence defined in [DEMO_SCENARIO.md](DEMO_SCENARIO.md)
- [ ] Three separate `dictionary.json` files exist under `.agentmesh/agents/{backend,frontend,database}/` after a run, each with the expected final state
- [ ] `input.json` queues show the 4 routed messages in the right directions
- [ ] The conflict on `backend.routes./api/users.auth_required` is detected and resolved by the priority table (backend wins on route auth) — visible in the dict history
- [ ] No LLM API calls in the hot path (verifiable by running with `ANTHROPIC_API_KEY=` unset — protocol still works end-to-end)

**Visualizer (MVP):**

- [ ] VS Code extension loads cleanly in an Extension Development Host on Windows 11
- [ ] Overlay webview connects to `ws://localhost:9900` and renders live events
- [ ] Three agent cards render, each with state badge and current task
- [ ] Dictionary tree updates on every `dict.mutated` event within 200ms
- [ ] Courier animations play on `message.sent`
- [ ] Conflict panel opens within 500ms of `conflict.detected` and clears on `conflict.resolved`
- [ ] Metrics bar increments in real time from `metrics.tick` events

**Visualizer (stretch — only if Day 4 has buffer):**

- [ ] pixel-agents JSONL shim drives the bottom panel with 3 pixel characters animating during the scenario

**Submission:**

- [ ] Public GitHub repo with README that walks a first-time user from `git clone` to a running demo in ≤ 10 commands
- [ ] ≤ 2-minute YouTube demo video showing the full scenario live
- [ ] Pitch deck PDF uploaded to Devpost
- [ ] Devpost submission complete per checklist

## 6. Success metrics (what makes this strong)

These map to the judging criteria seen in the materials:

| Judging criterion | How AgentMesh scores |
|---|---|
| **Challenge-Solution Fit** (3★) | Direct: the challenge asks for infrastructure *for* AI-to-AI, not retrofitted human tools. AgentMesh is literally that — file-as-interface, sidecar mediation, deterministic protocol. |
| **Technological Execution** (3★) | Custom diff engine, dependency-map router, priority-based conflict resolver, WebSocket event bus, JSONL shim, React overlay, all running locally with zero LLM calls on the hot path. **Not a prompt wrapper — demonstrably runs without any LLM at all.** |
| **Product Thinking / UI-UX** (1★) | Side-by-side visualization: pixel-agents shows *who* is working; overlay shows *what they're actually exchanging*. Data you can inspect vs. animation you can enjoy. |
| **Originality & Insight** (1★) | Framing is non-obvious: the scripted-agent demo is the proof that this is infrastructure, not a wrapper. |
| **Evidence of Real Demand** (1★) | Pain points grounded in Ishaan's original ideation transcript; pitch deck includes a user-interview quote slide. |

## 7. Non-goals

- We are **not** building a new orchestrator. Orchestrators consume AgentMesh; they don't replace it.
- We are **not** choosing models for users. Model selection is upstream.
- We are **not** generating runnable application code during the demo. The "work product" is coordinated dictionary state.
- We are **not** shipping to the VS Code Marketplace during the hackathon. Local dev host only.
- We are **not** modifying pixel-agents. We coexist via the shim.

## 8. Risks and fallback ladder

| Risk | Likelihood | Mitigation / fallback |
|---|---|---|
| Day 2 EOD: WebSocket server not up | Medium | P1 delivers `mesh/mock_events.jsonl` by end of Day 1 with the full scenario pre-recorded. P2 develops overlay against the mock file, swaps to live socket when ready. |
| Day 4: live demo flaky during recording | Low | Record the event stream once cleanly (session.jsonl is teed to disk by the server), then replay it into the overlay for the final take. Protocol is still real; only the timing source changes. |
| pixel-agents shim (stretch) eats Day 4 | Medium | Hard cut at Day 4 hour 8 — if the shim isn't showing characters, ship with overlay only and mention pixel-agents in pitch slides as "future integration." |
| pixel-agents paid furniture assets | None | Irrelevant to our repo. We don't commit any pixel-agents assets; shim (if built) only writes JSONL elsewhere on disk. |
| Windows 11 file-locking on concurrent writes | Medium | Atomic writes (`tempfile` + `os.replace`) tested on day 1. If issues persist, fall back to single-process Mini Agent manager (threads instead of processes). |
| Scope creep | High (always) | This PRD's §4.3 cut list is binding. If a task doesn't map to §4.1, it does not ship. |

## 9. Open questions

- Submission timestamp on Apr 25 — exact time + timezone (GMT+8) to set the final cutoff? *(captured here to resolve before Day 4)*
- Who owns the Devpost submission form fill? *(P3 or P4; defaults to P2 if ambiguous at Day 4 hour 4)*

## 10. Related docs

- [ARCHITECTURE.md](ARCHITECTURE.md) — MVP architecture
- [WEBSOCKET_SCHEMA.md](WEBSOCKET_SCHEMA.md) — event contract
- [DEMO_SCENARIO.md](DEMO_SCENARIO.md) — 90-second timeline
- [PLAN.md](PLAN.md) — 4-day execution plan
