"""Type B (semantic cross-reference) conflict rule evaluation.

docs/ARCHITECTURE.md §7.3 — a rule fires only when the trigger matches AND
the peer dictionary is missing the required cross-reference path.
"""
from __future__ import annotations

from mesh.conflict import RULES, ConflictRule, evaluate_rules


BACKEND_PATH = "backend.routes./api/users.auth_required"


def test_rule_fires_when_peer_missing_required_path() -> None:
    peer_dicts = {
        "frontend": {
            "_meta": {"agent_id": "frontend"},
            "frontend": {
                "api_calls": {
                    "/api/users": {"method": "GET", "headers": {}},
                },
            },
        },
    }
    matches = evaluate_rules(
        trigger_agent="backend",
        change_path=BACKEND_PATH,
        change_value=True,
        peer_dicts=peer_dicts,
    )
    assert len(matches) == 1
    m = matches[0]
    assert m.rule.id == "auth_required_on_route"
    assert m.captured == {"route": "/api/users"}
    assert m.required_peer_path == "api_calls./api/users.headers.Authorization"
    assert m.peer_has_required is False
    assert "/api/users" in m.resolution_message


def test_rule_does_not_fire_when_peer_already_has_required_path() -> None:
    peer_dicts = {
        "frontend": {
            "_meta": {"agent_id": "frontend"},
            "frontend": {
                "api_calls": {
                    "/api/users": {
                        "method": "GET",
                        "headers": {"Authorization": "Bearer {{token}}"},
                    },
                },
            },
        },
    }
    matches = evaluate_rules(
        trigger_agent="backend",
        change_path=BACKEND_PATH,
        change_value=True,
        peer_dicts=peer_dicts,
    )
    assert matches == []


def test_rule_does_not_fire_when_trigger_value_predicate_false() -> None:
    # auth_required is being flipped OFF (False). Rule predicate is `v is True`.
    peer_dicts = {"frontend": {"frontend": {"api_calls": {}}}}
    matches = evaluate_rules(
        trigger_agent="backend",
        change_path=BACKEND_PATH,
        change_value=False,
        peer_dicts=peer_dicts,
    )
    assert matches == []


def test_rule_does_not_fire_when_trigger_path_does_not_match() -> None:
    peer_dicts = {"frontend": {"frontend": {"api_calls": {}}}}
    # A different backend change that shouldn't trip the auth rule.
    matches = evaluate_rules(
        trigger_agent="backend",
        change_path="backend.models.User.fields.id",
        change_value="int",
        peer_dicts=peer_dicts,
    )
    assert matches == []


def test_rule_does_not_fire_when_trigger_agent_does_not_match() -> None:
    peer_dicts = {"frontend": {"frontend": {"api_calls": {}}}}
    matches = evaluate_rules(
        trigger_agent="frontend",  # rule targets backend
        change_path="frontend.routes./api/users.auth_required",
        change_value=True,
        peer_dicts=peer_dicts,
    )
    assert matches == []


def test_rules_list_ships_the_demo_rule() -> None:
    ids = [r.id for r in RULES]
    assert "auth_required_on_route" in ids
    rule = next(r for r in RULES if r.id == "auth_required_on_route")
    assert isinstance(rule, ConflictRule)
    assert rule.trigger_agent == "backend"
    assert rule.required_peer_agent == "frontend"
    assert rule.winner == "backend"
