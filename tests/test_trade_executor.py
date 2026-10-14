"""Tests for the controlled virtual-trade executor."""

import copy

import pytest

from src.config_loader import load_policy
from src.portfolio import create_virtual_portfolio
from src.trade_executor import (
    EXECUTED,
    REJECTED,
    execute_virtual_buy,
)
from src.approval_queue import create_proposal_hash

@pytest.fixture
def policy() -> dict:
    """Return the governing agent policy."""
    return load_policy()


@pytest.fixture
def portfolio() -> dict:
    """Return a new simulated portfolio."""
    return create_virtual_portfolio(100000.0)


@pytest.fixture
def proposal() -> dict:
    """Return a valid simulated BUY proposal."""
    return {
        "action_type": "manage_virtual_portfolio",
        "symbol": "MED",
        "order_side": "BUY",
        "trade_value": 2500.0,
        "position_percentage": 2.5,
        "uses_real_money": False,
        "requires_human_approval": True,
        "source_decision": "BUY",
    }


@pytest.fixture
def gate_result() -> dict:
    """Return a valid policy-gate result."""
    return {
        "action_type": "manage_virtual_portfolio",
        "governance_result": "REQUIRE_APPROVAL",
        "reason": (
            "The originating decision requires human approval."
        ),
        "policy_version": "1.0",
        "executed": False,
    }


@pytest.fixture
def approval_record(proposal: dict) -> dict:
    """Return explicit approval for the exact virtual trade."""

    return {
        "approved": True,
        "approved_by": "Jon Evans",
        "symbol": "MED",
        "proposal_hash": create_proposal_hash(proposal),
    }


def test_approved_virtual_buy_is_executed(
    portfolio: dict,
    proposal: dict,
    gate_result: dict,
    approval_record: dict,
    policy: dict,
) -> None:
    """An approved simulated BUY should update the portfolio."""

    updated, result = execute_virtual_buy(
        portfolio=portfolio,
        proposal=proposal,
        gate_result=gate_result,
        approval_record=approval_record,
        execution_price=50.0,
        policy=policy,
    )

    assert result["execution_status"] == EXECUTED
    assert result["portfolio_updated"] is True
    assert updated["cash_balance"] == 97500.0
    assert updated["positions"]["MED"]["quantity"] == 50.0
    assert updated["positions"]["MED"]["market_value"] == 2500.0
    assert updated["invested_market_value"] == 2500.0
    assert updated["total_portfolio_value"] == 100000.0
    assert len(updated["transactions"]) == 1
    assert updated["transactions"][0]["uses_real_money"] is False


def test_successful_execution_does_not_mutate_input(
    portfolio: dict,
    proposal: dict,
    gate_result: dict,
    approval_record: dict,
    policy: dict,
) -> None:
    """Execution should return a new portfolio object."""

    original = copy.deepcopy(portfolio)

    execute_virtual_buy(
        portfolio=portfolio,
        proposal=proposal,
        gate_result=gate_result,
        approval_record=approval_record,
        execution_price=50.0,
        policy=policy,
    )

    assert portfolio == original


def test_missing_human_approval_is_rejected(
    portfolio: dict,
    proposal: dict,
    gate_result: dict,
    policy: dict,
) -> None:
    """A BUY cannot execute without recorded approval."""

    updated, result = execute_virtual_buy(
        portfolio=portfolio,
        proposal=proposal,
        gate_result=gate_result,
        approval_record=None,
        execution_price=50.0,
        policy=policy,
    )

    assert result["execution_status"] == REJECTED
    assert result["portfolio_updated"] is False
    assert updated == portfolio


def test_approval_for_wrong_symbol_is_rejected(
    portfolio: dict,
    proposal: dict,
    gate_result: dict,
    approval_record: dict,
    policy: dict,
) -> None:
    """Approval must match the proposed asset."""

    approval_record["symbol"] = "AUR"

    updated, result = execute_virtual_buy(
        portfolio=portfolio,
        proposal=proposal,
        gate_result=gate_result,
        approval_record=approval_record,
        execution_price=50.0,
        policy=policy,
    )

    assert result["execution_status"] == REJECTED
    assert updated == portfolio


def test_blocked_trade_is_rejected(
    portfolio: dict,
    proposal: dict,
    gate_result: dict,
    approval_record: dict,
    policy: dict,
) -> None:
    """A BLOCK result cannot be overridden by approval."""

    gate_result["governance_result"] = "BLOCK"

    updated, result = execute_virtual_buy(
        portfolio=portfolio,
        proposal=proposal,
        gate_result=gate_result,
        approval_record=approval_record,
        execution_price=50.0,
        policy=policy,
    )

    assert result["execution_status"] == REJECTED
    assert updated == portfolio


def test_real_money_trade_is_rejected(
    portfolio: dict,
    proposal: dict,
    gate_result: dict,
    approval_record: dict,
    policy: dict,
) -> None:
    """The executor must reject real-money activity."""

    proposal["uses_real_money"] = True

    updated, result = execute_virtual_buy(
        portfolio=portfolio,
        proposal=proposal,
        gate_result=gate_result,
        approval_record=approval_record,
        execution_price=50.0,
        policy=policy,
    )

    assert result["execution_status"] == REJECTED
    assert updated == portfolio


def test_trade_above_policy_limit_is_rejected(
    portfolio: dict,
    proposal: dict,
    gate_result: dict,
    approval_record: dict,
    policy: dict,
) -> None:
    """A trade above $5,000 must not execute."""

    proposal["trade_value"] = 5000.01

    updated, result = execute_virtual_buy(
        portfolio=portfolio,
        proposal=proposal,
        gate_result=gate_result,
        approval_record=approval_record,
        execution_price=50.0,
        policy=policy,
    )

    assert result["execution_status"] == REJECTED
    assert updated == portfolio


def test_insufficient_virtual_cash_is_rejected(
    portfolio: dict,
    proposal: dict,
    gate_result: dict,
    approval_record: dict,
    policy: dict,
) -> None:
    """The virtual account cannot spend unavailable cash."""

    portfolio["cash_balance"] = 1000.0

    updated, result = execute_virtual_buy(
        portfolio=portfolio,
        proposal=proposal,
        gate_result=gate_result,
        approval_record=approval_record,
        execution_price=50.0,
        policy=policy,
    )

    assert result["execution_status"] == REJECTED
    assert updated == portfolio


@pytest.mark.parametrize(
    "execution_price",
    [None, "50.00", 0, -1.0, True],
)
def test_invalid_execution_price_is_rejected(
    execution_price,
    portfolio: dict,
    proposal: dict,
    gate_result: dict,
    approval_record: dict,
    policy: dict,
) -> None:
    """Malformed or nonpositive prices must be rejected."""

    updated, result = execute_virtual_buy(
        portfolio=portfolio,
        proposal=proposal,
        gate_result=gate_result,
        approval_record=approval_record,
        execution_price=execution_price,
        policy=policy,
    )

    assert result["execution_status"] == REJECTED
    assert updated == portfolio


def test_position_above_policy_limit_is_rejected(
    portfolio: dict,
    proposal: dict,
    gate_result: dict,
    approval_record: dict,
    policy: dict,
) -> None:
    """A trade cannot push one asset above 20%."""

    portfolio["cash_balance"] = 81000.0
    portfolio["invested_market_value"] = 19000.0
    portfolio["positions"]["MED"] = {
        "symbol": "MED",
        "quantity": 380.0,
        "average_cost": 50.0,
        "latest_price": 50.0,
        "market_value": 19000.0,
        "unrealized_gain_loss": 0.0,
    }

    updated, result = execute_virtual_buy(
        portfolio=portfolio,
        proposal=proposal,
        gate_result=gate_result,
        approval_record=approval_record,
        execution_price=50.0,
        policy=policy,
    )

    assert result["execution_status"] == REJECTED
    assert updated == portfolio


def test_sell_order_is_rejected(
    portfolio: dict,
    proposal: dict,
    gate_result: dict,
    approval_record: dict,
    policy: dict,
) -> None:
    """The BUY-only executor must reject SELL orders."""

    proposal["order_side"] = "SELL"

    updated, result = execute_virtual_buy(
        portfolio=portfolio,
        proposal=proposal,
        gate_result=gate_result,
        approval_record=approval_record,
        execution_price=50.0,
        policy=policy,
    )

    assert result["execution_status"] == REJECTED
    assert updated == portfolio

def test_approval_cannot_be_reused_for_modified_trade(
    portfolio: dict,
    proposal: dict,
    gate_result: dict,
    approval_record: dict,
    policy: dict,
) -> None:
    """Approval for one amount must not authorize another."""

    proposal["trade_value"] = 4000.0

    updated, result = execute_virtual_buy(
        portfolio=portfolio,
        proposal=proposal,
        gate_result=gate_result,
        approval_record=approval_record,
        execution_price=50.0,
        policy=policy,
    )

    assert result["execution_status"] == REJECTED
    assert result["portfolio_updated"] is False
    assert updated == portfolio