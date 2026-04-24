"""Drive the 6-agent showcase timeline by mutating dictionary.json files.

Run `python -m mesh.run --config demo/config.yaml` in one terminal first;
this script pumps a ~50-second choreographed timeline against the running
bus from a second terminal. Six Mini Agents watch dictionary.json mtime,
diff, route, and fire two Type B rules:

  1. `researcher.contracts.<route>.breaking_change=True`
     requires `tests.cases.<route>.migration_test`
  2. `reviewer.approvals.<route>.security_required=True`
     requires `formatter.lint_rules.<route>.security_check`

No LLM calls. Every action is a dictionary mutation or a state flip.
"""
from __future__ import annotations

import time
from pathlib import Path

from mesh.dict_store import DictStore, atomic_write_json


ROOT = Path(".agentmesh/agents")
AGENTS = ("orchestrator", "researcher", "tests", "formatter", "reviewer", "agent-6")


def _store(agent: str) -> DictStore:
    store = DictStore(ROOT / agent / "dictionary.json", agent_id=agent)
    store.load()
    return store


def set_path(agent: str, dotpath: str, value) -> None:
    store = _store(agent)
    store.set(dotpath, value)
    print(f"[{agent}] set {dotpath}")


def write_state(agent: str, state: str, current_task: str = "") -> None:
    path = ROOT / agent / "summary.json"
    atomic_write_json(path, {"state": state, "current_task": current_task})
    print(f"[{agent}] -> {state} {current_task}")


def _init_agent(agent: str) -> None:
    (ROOT / agent).mkdir(parents=True, exist_ok=True)
    atomic_write_json(
        ROOT / agent / "dictionary.json",
        {"_meta": {"agent_id": agent, "version": 0}, agent: {}},
    )
    atomic_write_json(ROOT / agent / "input.json", {"queue": []})
    atomic_write_json(
        ROOT / agent / "summary.json",
        {"state": "IDLE", "current_task": ""},
    )


def main() -> int:
    for a in AGENTS:
        _init_agent(a)

    print("[demo] six agents on disk — showcase scenario begins in 2s")
    time.sleep(2.0)

    # T+02 orchestrator kicks the plan off
    write_state("orchestrator", "WORKING", "Planning user-auth feature")
    time.sleep(1.5)
    set_path("orchestrator", "orchestrator.plan.feature", "user-auth")
    time.sleep(1.5)
    set_path("orchestrator", "orchestrator.plan.subtasks",
             ["research_api", "resolve_deps", "write_tests",
              "lint", "review", "merge"])
    time.sleep(1.5)

    # T+07 researcher + agent-6 wake up
    write_state("researcher", "WORKING", "Drafting /api/users contract")
    write_state("agent-6", "WORKING", "Resolving bcrypt dependency")
    time.sleep(1.5)

    # T+09 researcher publishes the contract (fans to tests + formatter)
    set_path("researcher", "researcher.contracts./api/users.fields", {
        "id": "int", "email": "string", "password_hash": "string",
    })
    time.sleep(1.8)

    # T+11 tests + formatter wake up on the new contract
    write_state("tests", "WORKING", "Authoring /api/users test cases")
    write_state("formatter", "WORKING", "Configuring lint rules for /api/users")
    time.sleep(1.5)

    # T+13 agent-6 publishes a dependency pin (fans to reviewer + orchestrator)
    set_path("agent-6", "agent-6.dependencies.bcrypt", {
        "version": "4.0.1", "checksum": "sha256:abc123",
    })
    time.sleep(1.8)

    # T+15 tests publishes happy-path cases (fans to reviewer)
    set_path("tests", "tests.cases./api/users.happy_path", {
        "assertions": 3, "status": "draft",
    })
    time.sleep(1.8)

    # T+17 formatter publishes initial style (fans to reviewer)
    set_path("formatter", "formatter.lint_rules./api/users.style", "PEP8")
    time.sleep(1.8)

    # T+19 reviewer wakes up
    write_state("reviewer", "WORKING", "Reviewing /api/users")
    time.sleep(1.5)

    # T+21 CONFLICT #1 — researcher flags a breaking change.
    # Rule `breaking_change_needs_migration_test` fires because
    # tests.cases./api/users.migration_test is missing.
    set_path("researcher", "researcher.contracts./api/users.breaking_change", True)
    time.sleep(2.5)

    # T+23 tests reacts to the resolution
    write_state("tests", "BLOCKED", "Adding migration test (resolution)")
    time.sleep(1.5)

    # T+25 tests applies the resolution
    set_path("tests", "tests.cases./api/users.migration_test", {
        "from_version": "0.9", "to_version": "1.0", "status": "authored",
    })
    time.sleep(1.5)
    write_state("tests", "WORKING", "Finalizing tests")
    time.sleep(1.5)

    # T+28 reviewer drops an initial approval
    set_path("reviewer", "reviewer.approvals./api/users.initial", True)
    time.sleep(1.8)

    # T+30 CONFLICT #2 — reviewer demands security coverage.
    # Rule `security_review_needs_lint_check` fires because
    # formatter.lint_rules./api/users.security_check is missing.
    set_path("reviewer", "reviewer.approvals./api/users.security_required", True)
    time.sleep(2.5)

    # T+33 formatter reacts
    write_state("formatter", "BLOCKED", "Enabling security lint (resolution)")
    time.sleep(1.5)

    # T+34 formatter applies the resolution
    set_path("formatter", "formatter.lint_rules./api/users.security_check", True)
    time.sleep(1.5)
    write_state("formatter", "WORKING", "Finalizing lint rules")
    time.sleep(1.5)

    # T+37 reviewer signs off
    set_path("reviewer", "reviewer.approvals./api/users.approved", True)
    time.sleep(1.8)

    # T+39 orchestrator wraps up
    write_state("orchestrator", "WORKING", "Merging /api/users")
    time.sleep(1.0)
    set_path("orchestrator", "orchestrator.plan.status", "merged")
    time.sleep(1.8)

    # T+42 agents wind down
    write_state("researcher", "COMPLETED")
    time.sleep(0.8)
    write_state("tests", "COMPLETED")
    time.sleep(0.8)
    write_state("formatter", "COMPLETED")
    time.sleep(0.8)
    write_state("reviewer", "COMPLETED")
    time.sleep(0.8)
    write_state("agent-6", "COMPLETED")
    time.sleep(0.8)
    write_state("orchestrator", "COMPLETED")
    time.sleep(1.0)

    print("[demo] showcase scenario complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
