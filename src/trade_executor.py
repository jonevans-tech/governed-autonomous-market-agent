"""Controlled execution of approved virtual portfolio trades."""

from __future__ import annotations

import copy
import math
import uuid
from datetime import datetime, timezone
from typing import Any
from src.approval_queue import create_proposal_hash


EXECUTED = "EXECUTED"
REJECTED = "REJECTED"

VALID_GATE_RESULTS = {
    "ALLOW",
    "REQUIRE_APPROVAL",
}


def reject_trade(reason: str) -> dict[str, Any]:
    """Create a standard result for a rejected virtual trade."""

    return {
        "execution_status": REJECTED,
        "reason": reason,
        "portfolio_updated": False,
        "transaction": None,
    }


def is_positive_number(value: Any) -> bool:
    """Return True only for a finite positive numeric value."""

    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    )


def has_valid_human_approval(
    approval_record: Any,
    proposal: dict[str, Any],
) -> bool:
    """Verify approval for the exact proposed trade."""

    if not isinstance(approval_record, dict):
        return False

    if not isinstance(proposal, dict):
        return False

    symbol = proposal.get("symbol")

    return (
        approval_record.get("approved") is True
        and approval_record.get("approved_by") not in (None, "")
        and approval_record.get("symbol") == symbol
        and approval_record.get("proposal_hash")
        == create_proposal_hash(proposal)
    )


def execute_virtual_buy(
    portfolio: dict[str, Any],
    proposal: dict[str, Any],
    gate_result: dict[str, Any],
    approval_record: dict[str, Any] | None,
    execution_price: float,
    policy: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Execute one approved simulated BUY order."""

    original_portfolio = copy.deepcopy(portfolio)

    if not isinstance(portfolio, dict):
        return original_portfolio, reject_trade(
            "The portfolio is malformed."
        )

    if portfolio.get("portfolio_type") != "simulation_only":
        return original_portfolio, reject_trade(
            "Only simulation portfolios can be modified."
        )

    if not isinstance(proposal, dict):
        return original_portfolio, reject_trade(
            "The trade proposal is malformed."
        )

    if proposal.get("action_type") != "manage_virtual_portfolio":
        return original_portfolio, reject_trade(
            "Only virtual portfolio actions can be executed."
        )

    if proposal.get("uses_real_money") is not False:
        return original_portfolio, reject_trade(
            "Real-money activity is prohibited."
        )

    if proposal.get("order_side") != "BUY":
        return original_portfolio, reject_trade(
            "This executor currently supports BUY orders only."
        )

    symbol = proposal.get("symbol")

    if not isinstance(symbol, str) or not symbol.strip():
        return original_portfolio, reject_trade(
            "A valid asset symbol is required."
        )

    symbol = symbol.strip().upper()

    if not isinstance(gate_result, dict):
        return original_portfolio, reject_trade(
            "A valid policy-gate result is required."
        )

    if (
        gate_result.get("action_type")
        != proposal.get("action_type")
    ):
        return original_portfolio, reject_trade(
            "The policy-gate result does not match the proposal."
        )

    governance_result = gate_result.get("governance_result")

    if governance_result == "BLOCK":
        return original_portfolio, reject_trade(
            "The policy gate blocked this trade."
        )

    if governance_result not in VALID_GATE_RESULTS:
        return original_portfolio, reject_trade(
            "The policy-gate result is not recognized."
        )

    if gate_result.get("executed") is not False:
        return original_portfolio, reject_trade(
            "The proposal has an invalid prior execution state."
        )

    if not has_valid_human_approval(
        approval_record,
        proposal,
    ):
        return original_portfolio, reject_trade(
            "Explicit human approval is required."
        )

    if not isinstance(policy, dict):
        return original_portfolio, reject_trade(
            "A valid governing policy is required."
        )

    if policy.get("operating_mode") != "autonomous_sandbox":
        return original_portfolio, reject_trade(
            "The executor requires autonomous sandbox mode."
        )

    financial_limits = policy.get("financial_limits", {})

    if not isinstance(financial_limits, dict):
        return original_portfolio, reject_trade(
            "The financial policy limits are malformed."
        )

    maximum_trade_value = financial_limits.get(
        "maximum_trade_value"
    )
    maximum_position_percentage = financial_limits.get(
        "maximum_position_percentage"
    )

    if not is_positive_number(maximum_trade_value):
        return original_portfolio, reject_trade(
            "The maximum trade limit is invalid."
        )

    if not is_positive_number(maximum_position_percentage):
        return original_portfolio, reject_trade(
            "The maximum position limit is invalid."
        )

    trade_value = proposal.get("trade_value")

    if not is_positive_number(trade_value):
        return original_portfolio, reject_trade(
            "The proposed trade value is invalid."
        )

    if trade_value > maximum_trade_value:
        return original_portfolio, reject_trade(
            "The trade exceeds the maximum virtual trade value."
        )

    if not is_positive_number(execution_price):
        return original_portfolio, reject_trade(
            "The execution price must be positive."
        )

    cash_balance = portfolio.get("cash_balance")
    total_portfolio_value = portfolio.get(
        "total_portfolio_value"
    )

    if not is_positive_number(cash_balance):
        return original_portfolio, reject_trade(
            "The portfolio cash balance is invalid."
        )

    if trade_value > cash_balance:
        return original_portfolio, reject_trade(
            "The portfolio has insufficient virtual cash."
        )

    if not is_positive_number(total_portfolio_value):
        return original_portfolio, reject_trade(
            "The total portfolio value is invalid."
        )

    positions = portfolio.get("positions")

    if not isinstance(positions, dict):
        return original_portfolio, reject_trade(
            "The portfolio positions are malformed."
        )

    current_position = positions.get(symbol, {})

    if not isinstance(current_position, dict):
        return original_portfolio, reject_trade(
            "The existing position is malformed."
        )

    current_quantity = current_position.get(
        "quantity",
        0.0,
    )

    if (
        not isinstance(current_quantity, (int, float))
        or isinstance(current_quantity, bool)
        or not math.isfinite(current_quantity)
        or current_quantity < 0
    ):
        return original_portfolio, reject_trade(
            "The existing position quantity is invalid."
        )

    current_position_value = (
        current_quantity * execution_price
    )
    new_position_value = (
        current_position_value + trade_value
    )
    new_position_percentage = (
        new_position_value / total_portfolio_value
    ) * 100

    if new_position_percentage > maximum_position_percentage:
        return original_portfolio, reject_trade(
            "The trade would exceed the maximum position percentage."
        )

    transactions = portfolio.get("transactions")

    if not isinstance(transactions, list):
        return original_portfolio, reject_trade(
            "The portfolio transaction history is malformed."
        )

    purchased_quantity = trade_value / execution_price
    new_quantity = current_quantity + purchased_quantity

    current_average_cost = current_position.get(
        "average_cost",
        0.0,
    )

    if (
        current_quantity > 0
        and not is_positive_number(current_average_cost)
    ):
        return original_portfolio, reject_trade(
            "The existing position average cost is invalid."
        )

    existing_cost = current_quantity * current_average_cost
    new_average_cost = (
        existing_cost + trade_value
    ) / new_quantity

    executed_at = datetime.now(timezone.utc).isoformat()

    transaction = {
        "transaction_id": str(uuid.uuid4()),
        "executed_at": executed_at,
        "portfolio_type": "simulation_only",
        "symbol": symbol,
        "order_side": "BUY",
        "quantity": round(purchased_quantity, 8),
        "execution_price": round(execution_price, 2),
        "trade_value": round(trade_value, 2),
        "approved_by": approval_record["approved_by"],
        "governance_result": governance_result,
        "uses_real_money": False,
    }

    updated_portfolio = copy.deepcopy(portfolio)

    updated_portfolio["cash_balance"] = round(
        cash_balance - trade_value,
        2,
    )

    updated_portfolio["positions"][symbol] = {
        "symbol": symbol,
        "quantity": round(new_quantity, 8),
        "average_cost": round(new_average_cost, 4),
        "latest_price": round(execution_price, 2),
        "market_value": round(new_position_value, 2),
        "unrealized_gain_loss": round(
            new_position_value
            - (new_quantity * new_average_cost),
            2,
        ),
    }

    updated_portfolio["transactions"].append(
        transaction
    )

    invested_market_value = sum(
        position["market_value"]
        for position in updated_portfolio[
            "positions"
        ].values()
    )

    total_unrealized_gain_loss = sum(
        position["unrealized_gain_loss"]
        for position in updated_portfolio[
            "positions"
        ].values()
    )

    updated_portfolio["invested_market_value"] = round(
        invested_market_value,
        2,
    )
    updated_portfolio["total_portfolio_value"] = round(
        updated_portfolio["cash_balance"]
        + invested_market_value,
        2,
    )
    updated_portfolio[
        "total_unrealized_gain_loss"
    ] = round(
        total_unrealized_gain_loss,
        2,
    )
    updated_portfolio["updated_at"] = executed_at

    result = {
        "execution_status": EXECUTED,
        "reason": (
            "The approved virtual BUY order was executed."
        ),
        "portfolio_updated": True,
        "transaction": transaction,
    }

    return updated_portfolio, result