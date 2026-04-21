# demo — Scripted Agent Scenario

Owner: **P1 (Ishaan)**, after mesh/ core is running.

This directory holds the 90-second choreographed scenario used for the demo video.

Three scripted Python "major agents" that mutate their dictionaries on a timeline:

- `backend_agent.py` — simulates a Claude Code backend session
- `frontend_agent.py` — simulates a Cursor/Gemini frontend session
- `database_agent.py` — simulates an Ollama DB session

Each is a plain Python script that:
1. Creates an AgentMesh Mini Agent sidecar (from `mesh/`)
2. Mutates its `dictionary.json` on a scripted timeline
3. Exits cleanly after the scenario completes

There are **no LLM calls** in demo/. The whole point is to prove AgentMesh is protocol infrastructure — it works without any LLM in the loop. The scripts are stand-ins for what would, in production, be real coding agents.

## Entry point

```
python demo/run_scenario.py
```

Runs the three agents in parallel, drives them through the timeline in [../docs/DEMO_SCENARIO.md](../docs/DEMO_SCENARIO.md), and terminates cleanly.
