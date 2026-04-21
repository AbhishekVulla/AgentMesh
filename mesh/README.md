# mesh — AgentMesh Python Protocol

Owner: **P1 (Ishaan)**

This directory holds the Python implementation of the AgentMesh protocol:

- `mini_agent.py` — sidecar process paired with one major agent
- `dict_store.py` — nested dictionary store, dot-path addressing, atomic writes
- `diff_engine.py` — path-aware JSON diff
- `router.py` — dependency-map driven message routing
- `conflict.py` — priority-based conflict resolution (no LLM)
- `ws_server.py` — WebSocket event broadcaster (localhost:9900)
- `schemas/` — pydantic models for messages, dicts, events

See [../docs/PLAN.md](../docs/PLAN.md) for the day-by-day task list.
See [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) for the MVP architecture.
See [../docs/WEBSOCKET_SCHEMA.md](../docs/WEBSOCKET_SCHEMA.md) for the event contract.
