# AgentMesh

> **Infrastructure designed for AI-to-AI interaction — not retrofitted human-centered software for agent workflows.**

Hackathon submission for **strAIght up! Hackathon 2026** (Wavesparks / Lythe / Next Big Thing, 18-25 April 2026, Lorong AI @ One-North, Singapore):

> Most software infrastructure today assumes humans are the primary operators. But agentic systems increasingly need to coordinate with other agents, tools, and environments directly. How might we build infrastructure designed for AI-to-AI interaction, rather than retrofitting human-centered software for agent workflows?

## What AgentMesh is

A multi-agent communication protocol. Each major coding agent (Claude Code, Codex, Gemini, Ollama, or any scripted producer) is paired with a lightweight **Mini Agent sidecar** that owns three files:

- `context.json` — persistent state + relevant subscriptions from other agents
- `summary.json` — concise overview of what the agent is doing
- `input.json` — incoming message queue

Mini Agents communicate through a **dictionary store** addressable by dot-path (e.g. `backend.routes./api/users.auth_required`). They compute diffs, route changes through a configurable dependency map, and resolve conflicts deterministically — **no LLM calls on the hot path**.

## Why this matters

Current multi-agent systems either:

- Funnel everything through a heavyweight orchestrator (20-30% context loss, token explosion), or
- Retrofit human-centered tools (IDEs, chat threads, tickets) onto agent coordination.

AgentMesh is infrastructure-first: **file-as-interface, minimum viable context, sidecar mediation.** The protocol runs without any LLM in the loop — the protocol *is* the product.

## Architecture (MVP)

```
┌──────────┐   ┌──────────┐   ┌──────────┐
│ Agent A  │   │ Agent B  │   │ Agent C  │     Any producer: Claude Code,
│ (Major)  │   │ (Major)  │   │ (Major)  │     Codex, scripted Python, ...
└────┬─────┘   └────┬─────┘   └────┬─────┘
     v              v              v
┌──────────┐   ┌──────────┐   ┌──────────┐
│Mini Agent│<->│Mini Agent│<->│Mini Agent│     Python sidecar.
│ (Sidecar)│   │ (Sidecar)│   │ (Sidecar)│     File watcher, diff engine,
└────┬─────┘   └────┬─────┘   └────┬─────┘     router, conflict resolver.
     └──────────┬───┴──────────────┘
                v
         ┌──────────────┐
         │ WebSocket    │                      Event stream.
         │ :9900        │
         └──────┬───────┘
                v
    ┌─────────────────────────┐
    │ VS Code Visualizer      │                pixel-agents (characters in
    │ ┌────────┐ ┌──────────┐ │                a virtual office) + AgentMesh
    │ │pixel-  │ │AgentMesh │ │                overlay (live dict store,
    │ │agents  │ │overlay   │ │                message queue, conflict
    │ │(MIT)   │ │panel     │ │                panel, metrics).
    │ └────────┘ └──────────┘ │
    └─────────────────────────┘
```

## Repository layout

| Path | What | Owner |
|---|---|---|
| [mesh/](mesh/) | Python protocol — Mini Agent, dict store, diff engine, router, conflict resolver, WebSocket server | P1 (Ishaan) |
| [extension/](extension/) | VS Code extension — pixel-agents shim + AgentMesh overlay webview | P2 (Abhi) |
| [demo/](demo/) | Scripted Python agents that drive the 90-second demo scenario | P1 |
| [docs/](docs/) | PRD, ARCHITECTURE, WEBSOCKET_SCHEMA, DEMO_SCENARIO, PLAN, kickoff prompts | shared |

## Docs

- [docs/PRD.md](docs/PRD.md) — product spec for the hackathon submission
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — MVP architecture (trimmed from full system design)
- [docs/WEBSOCKET_SCHEMA.md](docs/WEBSOCKET_SCHEMA.md) — canonical event contract between backend and extension
- [docs/DEMO_SCENARIO.md](docs/DEMO_SCENARIO.md) — the 90-second demo timeline
- [docs/PLAN.md](docs/PLAN.md) — 4-day execution plan with P1/P2 split
- [docs/P1_KICKOFF.md](docs/P1_KICKOFF.md) — Claude Code kickoff prompt for Ishaan (P1, backend)
- [docs/P2_KICKOFF.md](docs/P2_KICKOFF.md) — Claude Code kickoff prompt for Abhi (P2, extension)

## Quickstart (when built)

```bash
# Terminal 1 — start the protocol backend
cd mesh
python -m mesh.run --config ../demo/config.yaml

# Terminal 2 — run the demo scenario
python demo/run_scenario.py

# VS Code — open the workspace, F5 to launch the extension dev host
# The extension connects to ws://localhost:9900 and shows the live session.
```

## Credits

- Visualizer built on top of [pablodelucca/pixel-agents](https://github.com/pablodelucca/pixel-agents) (MIT) — we use it unmodified via a JSONL shim.
- Protocol design from the full internal spec (see root-level `AgentMesh_System_Architecture.md` and `AgentMesh_PRD.docx` in the team workspace — not committed to this public repo).

## License

MIT — see [LICENSE](LICENSE).
