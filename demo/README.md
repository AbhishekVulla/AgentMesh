# demo/ — reference scenario

Configuration + scripted drivers for the 6-agent reference scenario described in [../docs/DEMO_SCENARIO.md](../docs/DEMO_SCENARIO.md). The protocol runs for real; the "agents" are Python functions that write dictionary mutations on a timeline.

## Files

- [`config.yaml`](config.yaml) — agents, directories, WebSocket port, tee path, duration budget
- [`dependency_map.yaml`](dependency_map.yaml) — publish/subscribe graph (see ARCHITECTURE.md §6)
- [`priority_table.yaml`](priority_table.yaml) — Type A conflict-resolution winners (see ARCHITECTURE.md §7.4)
- [`run_scenario.py`](run_scenario.py) — choreographed timeline; mutates dictionary files against a running `mesh.run`

## Running

Two terminals:

```bash
# Terminal 1 — start the protocol bus
python -m mesh.run --config demo/config.yaml --duration 180

# Terminal 2 — drive the scenario
python -m demo.run_scenario
```

Takes ~50 seconds. Produces ~13 dictionary mutations, 24 routed messages, and 2 Type B conflict resolutions. Session events tee'd to `.agentmesh/events/session.jsonl`.
