from typing import Any

from src.config_loader import load_policy


ALLOW = "ALLOW"
REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
BLOCK = "BLOCK"


def create_gate_result(
    proposal: dict[str, Any],
    result: str,
    reason: str,
    policy_version: str,
) -> dict[str, Any]:
    """Create a standard policy-gate response."""
    return {
        "action_type": proposal.get("action_type"),
        "governance_result": result,
        "reason": reason,
        "policy_version": policy_version,
        "executed": False,
    }


def evaluate_action(
    proposal: dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate a proposed action against governing policy."""
    if policy is None:
        policy = load_policy()

    policy_version = policy["policy_version"]
    action_type = proposal.get("action_type")

    if not action_type:
        return create_gate_result(
            proposal,
            BLOCK,
            "The proposal does not identify an action type.",
            policy_version,
        )

    if proposal.get("uses_real_money") is True:
        return create_gate_result(
            proposal,
            BLOCK,
            "Real-money activity is prohibited.",
            policy_version,
        )

    if action_type in policy["prohibited_actions"]:
        return create_gate_result(
            proposal,
            BLOCK,
            "The proposed action is explicitly prohibited.",
            policy_version,
        )

    if action_type == "manage_virtual_portfolio":
        return evaluate_virtual_trade(
            proposal,
            policy,
        )

    if action_type in policy["approval_required_actions"]:
        return create_gate_result(
            proposal,
            REQUIRE_APPROVAL,
            "The governing policy requires human approval.",
            policy_version,
        )

    if action_type in policy["allowed_actions"]:
        return create_gate_result(
            proposal,
            ALLOW,
            "The action is permitted in the autonomous sandbox.",
            policy_version,
        )

    return create_gate_result(
        proposal,
        BLOCK,
        "Unknown actions are blocked by default.",
        policy_version,
    )


def evaluate_virtual_trade(
    proposal: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    """Apply financial limits to a virtual trade proposal."""
    policy_version = policy["policy_version"]
    limits = policy["financial_limits"]

    trade_value = proposal.get("trade_value")
    position_percentage = proposal.get(
        "position_percentage",
        0.0,
    )

    if not isinstance(trade_value, (int, float)):
        return create_gate_result(
            proposal,
            BLOCK,
            "A virtual trade must include a numeric trade value.",
            policy_version,
        )

    if trade_value <= 0:
        return create_gate_result(
            proposal,
            BLOCK,
            "A virtual trade value must be greater than zero.",
            policy_version,
        )

    if position_percentage > limits[
        "maximum_position_percentage"
    ]:
        return create_gate_result(
            proposal,
            BLOCK,
            "The proposed position exceeds the portfolio limit.",
            policy_version,
        )

    if trade_value > limits["maximum_trade_value"]:
        return create_gate_result(
            proposal,
            REQUIRE_APPROVAL,
            "The virtual trade exceeds the automatic trade limit.",
            policy_version,
        )

    return create_gate_result(
        proposal,
        ALLOW,
        "The virtual trade is within all automatic limits.",
        policy_version,
    )


def demonstrate_policy_gate() -> None:
    """Evaluate example proposals without executing them."""
    proposals = [
        {
            "name": "Routine virtual trade",
            "action_type": "manage_virtual_portfolio",
            "trade_value": 2500.00,
            "position_percentage": 5.0,
            "uses_real_money": False,
        },
        {
            "name": "Large virtual trade",
            "action_type": "manage_virtual_portfolio",
            "trade_value": 7500.00,
            "position_percentage": 7.5,
            "uses_real_money": False,
        },
        {
            "name": "Real financial transaction",
            "action_type": "execute_real_financial_transaction",
            "trade_value": 1000.00,
            "uses_real_money": True,
        },
        {
            "name": "External social post",
            "action_type": "publish_external_content",
        },
        {
            "name": "Unrecognized tool request",
            "action_type": "run_unknown_tool",
        },
    ]

    print("Aureus policy-gate demonstration")
    print("================================")

    for proposal in proposals:
        gate_result = evaluate_action(proposal)

        print(
            f"{proposal['name']} | "
            f"{gate_result['governance_result']}"
        )
        print(f"  Reason: {gate_result['reason']}")
        print(f"  Executed: {gate_result['executed']}")


if __name__ == "__main__":
    demonstrate_policy_gate()
