import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.config_loader import load_agent_config
from src.decision_engine import create_decision_report
from src.observe_market import (
    create_market_observation,
    load_market_history,
)
from src.policy_gate import evaluate_action

from src.audit_log import append_audit_record
from src.memory import (
    create_empty_memory,
    load_memory,
    save_memory,
    update_memory,
)
from src.memory_context import add_memory_context

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CYCLE_STATE_PATH = (
    PROJECT_ROOT
    / "data"
    / "state"
    / "latest_agent_cycle.json"
)


def build_action_proposal(
    decision: dict[str, Any],
) -> dict[str, Any]:
    """Convert a recommendation into a governed proposal."""
    if decision["proposed_action"] == "BUY":
        return {
            "action_type": "manage_virtual_portfolio",
            "symbol": decision["symbol"],
            "order_side": "BUY",
            "trade_value": 2500.00,
            "position_percentage": 2.5,
            "uses_real_money": False,
            "requires_human_approval": decision[
            "requires_approval"
            ],
            "source_decision": decision["proposed_action"],
        }

    return {
        "action_type": "analyze_market_conditions",
        "symbol": decision["symbol"],
        "requested_market_action": decision[
            "proposed_action"
        ],
        "uses_real_money": False,
        "source_decision": decision["proposed_action"],
    }


def govern_decisions(
    decision_report: dict[str, Any],
) -> list[dict[str, Any]]:
    """Submit every proposed action to the policy gate."""
    governed_actions = []

    for decision in decision_report["decisions"]:
        proposal = build_action_proposal(decision)
        gate_result = evaluate_action(proposal)

        governed_actions.append(
            {
                "decision": decision,
                "proposal": proposal,
                "gate_result": gate_result,
            }
        )

    return governed_actions


def summarize_cycle(
    governed_actions: list[dict[str, Any]],
) -> dict[str, int]:
    """Count the policy-gate outcomes."""
    summary = {
        "allowed": 0,
        "approval_required": 0,
        "blocked": 0,
        "executed": 0,
    }

    for item in governed_actions:
        result = item["gate_result"]["governance_result"]

        if result == "ALLOW":
            summary["allowed"] += 1
        elif result == "REQUIRE_APPROVAL":
            summary["approval_required"] += 1
        elif result == "BLOCK":
            summary["blocked"] += 1

        if item["gate_result"]["executed"] is True:
            summary["executed"] += 1

    return summary


def run_agent_cycle(
    memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one complete governed autonomous-agent cycle."""
    config = load_agent_config()
    if memory is None:
        memory = create_empty_memory(
            config["identity"]["agent_name"]
        )
    started_at = datetime.now(timezone.utc).isoformat()

    market_rows = load_market_history()
    observation = create_market_observation(market_rows)
    decision_report = create_decision_report(observation)
    decision_report = add_memory_context(
    decision_report,
    memory,
)
    governed_actions = govern_decisions(decision_report)
    completed_at = datetime.now(timezone.utc).isoformat()

    return {
        "cycle_id": str(uuid4()),
        "agent_name": config["identity"]["agent_name"],
        "operating_mode": config["policy"]["operating_mode"],
        "started_at": started_at,
        "completed_at": completed_at,
        "observation": observation,
        "decision_report": decision_report,
        "governed_actions": governed_actions,
        "cycle_summary": summarize_cycle(governed_actions),
    }


def save_agent_cycle(
    cycle: dict[str, Any],
    file_path: Path = CYCLE_STATE_PATH,
) -> None:
    """Save the latest autonomous cycle as runtime state."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(cycle, file, indent=2)


def print_cycle_summary(cycle: dict[str, Any]) -> None:
    """Display the important results of one cycle."""
    print("Aureus autonomous agent cycle")
    print("=============================")
    print(f"Cycle ID: {cycle['cycle_id']}")
    print(f"Mode: {cycle['operating_mode']}")
    print()

    for item in cycle["governed_actions"]:
        decision = item["decision"]
        proposal = item["proposal"]
        gate_result = item["gate_result"]

        print(
            f"{decision['symbol']} | "
            f"Recommendation: "
            f"{decision['proposed_action']} | "
            f"Proposal: {proposal['action_type']} | "
            f"Gate: {gate_result['governance_result']}"
        )
        print(
            "  Memory: "
            f"{decision['memory_context']['memory_statement']}"
        )
    summary = cycle["cycle_summary"]

    print()
    print(f"Allowed proposals: {summary['allowed']}")
    print(
        "Approval-required proposals: "
        f"{summary['approval_required']}"
    )
    print(f"Blocked proposals: {summary['blocked']}")
    print(f"Executed actions: {summary['executed']}")


def main() -> None:
    config = load_agent_config()
    memory = load_memory(
        agent_name=config["identity"]["agent_name"]
    )

    cycle = run_agent_cycle(memory)
    save_agent_cycle(cycle)

    memory = update_memory(memory, cycle)
    save_memory(memory)

    audit_record = append_audit_record(cycle)
    print_cycle_summary(cycle)

    print()
    print("The autonomous cycle completed safely.")
    print("No financial transactions were executed.")
    print(f"Cycle state saved to: {CYCLE_STATE_PATH}")
    print(
        "Audit record hash: "
        f"{audit_record['record_hash']}"
    )
    print(
        "Cycles remembered: "
        f"{memory['total_cycles_remembered']}"
    )


if __name__ == "__main__":
    main()