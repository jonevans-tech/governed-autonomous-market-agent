import json
from datetime import datetime
from uuid import UUID

from src.agent_cycle import (
    build_action_proposal,
    govern_decisions,
    run_agent_cycle,
    save_agent_cycle,
    summarize_cycle,
)


def make_buy_decision():
    return {
        "symbol": "TST",
        "company_name": "Test Company",
        "proposed_action": "BUY",
        "requires_approval": True,
        "trade_executed": False,
    }


def test_buy_becomes_virtual_trade_proposal():
    proposal = build_action_proposal(
        make_buy_decision()
    )

    assert proposal["action_type"] == (
        "manage_virtual_portfolio"
    )
    assert proposal["order_side"] == "BUY"
    assert proposal["trade_value"] == 2500.00
    assert proposal["uses_real_money"] is False


def test_buy_proposal_carries_approval_requirement():
    proposal = build_action_proposal(
        make_buy_decision()
    )

    assert proposal["requires_human_approval"] is True


def test_non_buy_becomes_analysis_proposal():
    decision = {
        "symbol": "TST",
        "proposed_action": "WATCH",
        "requires_approval": False,
    }

    proposal = build_action_proposal(decision)

    assert proposal["action_type"] == (
        "analyze_market_conditions"
    )
    assert proposal["uses_real_money"] is False


def test_buy_reaches_gate_as_approval_required():
    decision_report = {
        "decisions": [make_buy_decision()]
    }

    governed_actions = govern_decisions(
        decision_report
    )
    gate_result = governed_actions[0]["gate_result"]

    assert gate_result["governance_result"] == (
        "REQUIRE_APPROVAL"
    )
    assert gate_result["executed"] is False


def test_every_decision_reaches_policy_gate():
    cycle = run_agent_cycle()

    decision_count = len(
        cycle["decision_report"]["decisions"]
    )
    governed_count = len(cycle["governed_actions"])

    assert governed_count == decision_count


def test_cycle_contains_valid_identifier():
    cycle = run_agent_cycle()

    cycle_identifier = UUID(cycle["cycle_id"])

    assert str(cycle_identifier) == cycle["cycle_id"]


def test_cycle_contains_valid_timestamps():
    cycle = run_agent_cycle()

    started_at = datetime.fromisoformat(
        cycle["started_at"]
    )
    completed_at = datetime.fromisoformat(
        cycle["completed_at"]
    )

    assert completed_at >= started_at
    assert started_at.tzinfo is not None
    assert completed_at.tzinfo is not None


def test_current_cycle_allows_four_analysis_proposals():
    cycle = run_agent_cycle()

    assert cycle["cycle_summary"] == {
        "allowed": 4,
        "approval_required": 0,
        "blocked": 0,
        "executed": 0,
    }


def test_cycle_executes_no_actions():
    cycle = run_agent_cycle()

    for item in cycle["governed_actions"]:
        assert item["gate_result"]["executed"] is False


def test_cycle_can_be_saved_as_json(tmp_path):
    cycle = run_agent_cycle()
    output_path = tmp_path / "agent_cycle.json"

    save_agent_cycle(cycle, output_path)

    saved_cycle = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert saved_cycle == cycle


def test_summary_counts_mixed_gate_results():
    governed_actions = [
        {
            "gate_result": {
                "governance_result": "ALLOW",
                "executed": False,
            }
        },
        {
            "gate_result": {
                "governance_result": "REQUIRE_APPROVAL",
                "executed": False,
            }
        },
        {
            "gate_result": {
                "governance_result": "BLOCK",
                "executed": False,
            }
        },
    ]

    summary = summarize_cycle(governed_actions)

    assert summary == {
        "allowed": 1,
        "approval_required": 1,
        "blocked": 1,
        "executed": 0,
    }
