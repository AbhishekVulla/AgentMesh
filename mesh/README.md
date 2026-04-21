# mesh/ — protocol core

Owner: **P1 (Ishaan)** on branch `p1-backend`. P2 does not edit this directory.

## Layout

```
mesh/
├── __init__.py              # package version
├── __main__.py              # `python -m mesh` → run.main
├── run.py                   # CLI entry: `python -m mesh.run --config …`
├── dict_store.py            # Atomic JSON store + dot-path addressing (Day 2)
├── diff_engine.py           # Path-aware nested dict diff (Day 2)
├── router.py                # dependency_map.yaml → per-target diff subsets (Day 2)
├── conflict.py              # Priority-table deterministic resolver (Day 2)
├── mini_agent.py            # Sidecar wiring watchdog → diff → route (Day 2)
├── ws_server.py             # websockets.serve on :9900 (Day 2)
├── mock_events.jsonl        # G2 deliverable — 56-event replay fixture for P2
├── schemas/
│   ├── events.py            # Pydantic-v2 discriminated union (9 variants)
│   └── events.schema.json   # Generated JSON Schema for P2 TypeScript types
└── tests/
    ├── test_schema_import.py       # Smoke: schema imports + round-trips
    └── _build_mock_events.py       # Fixture builder (regenerates mock_events.jsonl)
```

## Day 1 status (this branch)

- [x] Skeleton files exist — every module imports without error.
- [x] Pydantic models cover every event in `docs/WEBSOCKET_SCHEMA.md`.
- [x] `mesh/schemas/events.schema.json` generated and committed.
- [x] `mesh/mock_events.jsonl` hand-authored via `_build_mock_events.py`, 56
      schema-valid events, replays the full 26-second scenario.
- [ ] dict_store / diff_engine / router / conflict / mini_agent / ws_server
      bodies — **Day 2**. Each skeleton raises `NotImplementedError` with a
      pointer to the PLAN.md task that fills it in.

## Determinism rule

Every module here operates deterministically. **No LLM API calls, no network
fetches, no randomness on the hot path.** The full demo must run with
`ANTHROPIC_API_KEY=` and `OPENAI_API_KEY=` unset.

## Regenerating the mock event log

```bash
python -m mesh.tests._build_mock_events
```

If `docs/DEMO_SCENARIO.md` changes, re-run the builder and commit the diff.
