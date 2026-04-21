# demo/ — scripted 3-agent scenario

Owner: **P1 (Ishaan)** on branch `p1-backend`.

Files that end up here drive a deterministic, no-LLM replay of the scenario
in [../docs/DEMO_SCENARIO.md](../docs/DEMO_SCENARIO.md). The backend
protocol runs for real; the "agents" are just scripted Python that write
dictionary mutations on a timeline.

## Day 1 (this branch)

- [x] `config.yaml` — agents, dirs, WS port, tee path, duration budget
- [x] `dependency_map.yaml` — publish/subscribe graph (ARCHITECTURE.md §6)
- [x] `priority_table.yaml` — conflict-resolution winners (ARCHITECTURE.md §7)

## Day 3 (not yet on this branch)

- [ ] `backend_agent.py` — scripted backend producer
- [ ] `frontend_agent.py` — scripted frontend producer
- [ ] `database_agent.py` — scripted database producer
- [ ] `run_scenario.py` — spawns Mini Agent sidecars + the three scripted
      agents in parallel; exits when `mesh.session.ended` is emitted

## Smoke test (Day 1)

```bash
python -m mesh.run --config demo/config.yaml
```

Prints the registered agent IDs and the WebSocket endpoint. Day-2 will
replace the placeholder with a real session bootstrap.
