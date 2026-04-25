# mesh/ — protocol core

The Python package implementing the AgentMesh protocol: Mini Agent sidecar, dictionary store, diff engine, router, dual-mechanism conflict resolver, and WebSocket event bus.

## Layout

```
mesh/
├── __init__.py              # package version
├── __main__.py              # `python -m mesh` → run.main
├── run.py                   # session bootstrap: `python -m mesh.run --config ...`
├── dict_store.py            # Atomic JSON store + dot-path addressing
├── diff_engine.py           # Path-aware nested dict diff
├── router.py                # dependency_map.yaml → per-target diff subsets
├── conflict.py              # Dual-mechanism resolver (Type A priority + Type B rules)
├── mini_agent.py            # Sidecar wiring: watchdog → diff → route → conflict
├── ws_server.py             # websockets.serve on :9900
├── cli.py                   # `agentmesh` console script
├── client.py                # Python client library for the event stream
├── schemas/
│   ├── events.py            # Pydantic-v2 discriminated union (9 variants)
│   └── events.schema.json   # Generated JSON Schema
└── tests/
    ├── test_conflict_type_b.py   # Rule evaluation unit tests
    └── test_schema_import.py     # Schema import + round-trip
```

## Determinism rule

Every module here operates deterministically. The coordination layer is pure code — the protocol diffs, routes, and resolves conflicts without external dependencies on the hot path. Reproducible to the byte across runs.

## Running

```bash
python -m mesh.run --config ../demo/config.yaml --duration 180
```

Starts the WebSocket server on `ws://localhost:9900`, instantiates Mini Agent sidecars per the config, and tees every event to `.agentmesh/events/session.jsonl`.
