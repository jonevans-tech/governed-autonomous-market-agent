"""Integration tests for the approved-trade workflow."""

import copy

import pytest

from src.approval_queue import (
    APPROVED,
    CONSUMED,
    REJECTED as APPROVAL_REJECTED,
    review_approval_request,
    submit_approval_request,
)
from src.approved_trade_workflow import (
    process_approved_trade,
)
from src.config_loader import load_policy
from src.portfolio import create_virtual_portfolio
from src.trade_executor import (
    EXECUTED,
    REJECTED,
)


@pytest.fixture
def policy() -> dict:
    """Return the governing policy."""
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
    """Return an approval-required gate result."""
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
def empty_queue() -> dict:
    """Return an empty approval queue."""
    return {
        "schema_version": "1.0",
        "queue_type": "human_trade_approval",
        "requests": [],
    }


def create_request(
    queue: dict,
    proposal: dict,
    gate_result: dict,
) -> tuple[dict, dict]:
    """Submit one trade to the approval queue."""

    return submit_approval_request(
        queue=queue,
        proposal=proposal,
        gate_result=gate_result,
    )


def approve_request(
    queue: dict,
    approval_id: str,
) -> tuple[dict, dict]:
    """Approve one pending request."""

    return review_approval_request(
        queue=queue,
        approval_id=approval_id,
        decision="APPROVE",
        reviewed_by="Jon Evans",
        review_note="Approved for simulated execution.",
    )


def test_approved_trade_updates_portfolio_and_queue(
    empty_queue: dict,
    portfolio: dict,
    proposal: dict,
    gate_result: dict,
    policy: dict,
) -> None:
    """An approved request should execute and be consumed."""

    queued, request = create_request(
        empty_queue,
        proposal,
        gate_result,
    )
    approved_queue, _ = approve_request(
        queued,
        request["approval_id"],
    )

    updated_queue, updated_portfolio, result = (
        process_approved_trade(
            queue=approved_queue,
            portfolio=portfolio,
            approval_id=request["approval_id"],
            execution_price=50.0,
            policy=policy,
        )
    )

    assert result["execution_status"] == EXECUTED
    assert result["portfolio_updated"] is True
    assert result["approval_consumed"] is True
    assert result["approval_status"] == CONSUMED
    assert updated_portfolio["cash_balance"] == 97500.0
    assert updated_portfolio["positions"]["MED"][
        "quantity"
    ] == 50.0
    assert len(updated_portfolio["transactions"]) == 1
    assert updated_queue["requests"][0]["status"] == CONSUMED
    assert updated_queue["requests"][0][
        "transaction_id"
    ] == result["transaction"]["transaction_id"]


def test_workflow_does_not_mutate_inputs(
    empty_queue: dict,
    portfolio: dict,
    proposal: dict,
    gate_result: dict,
    policy: dict,
) -> None:
    """The workflow should return new state objects."""

    queued, request = create_request(
        empty_queue,
        proposal,
        gate_result,
    )
    approved_queue, _ = approve_request(
        queued,
        request["approval_id"],
    )

    original_queue = copy.deepcopy(approved_queue)
    original_portfolio = copy.deepcopy(portfolio)

    process_approved_trade(
        queue=approved_queue,
        portfolio=portfolio,
        approval_id=request["approval_id"],
        execution_price=50.0,
        policy=policy,
    )

    assert approved_queue == original_queue
    assert portfolio == original_portfolio


def test_pending_request_cannot_execute(
    empty_queue: dict,
    portfolio: dict,
    proposal: dict,
    gate_result: dict,
    policy: dict,
) -> None:
    """A pending request must not reach execution."""

    queued, request = create_request(
        empty_queue,
        proposal,
        gate_result,
    )

    with pytest.raises(
        ValueError,
        match="not approved",
    ):
        process_approved_trade(
            queue=queued,
            portfolio=portfolio,
            approval_id=request["approval_id"],
            execution_price=50.0,
            policy=policy,
        )


def test_rejected_request_cannot_execute(
    empty_queue: dict,
    portfolio: dict,
    proposal: dict,
    gate_result: dict,
    policy: dict,
) -> None:
    """A rejected human decision must stop execution."""

    queued, request = create_request(
        empty_queue,
        proposal,
        gate_result,
    )

    rejected_queue, rejected = review_approval_request(
        queue=queued,
        approval_id=request["approval_id"],
        decision="REJECT",
        reviewed_by="Jon Evans",
        review_note="Declined.",
    )

    assert rejected["status"] == APPROVAL_REJECTED

    with pytest.raises(
        ValueError,
        match="not approved",
    ):
        process_approved_trade(
            queue=rejected_queue,
            portfolio=portfolio,
            approval_id=request["approval_id"],
            execution_price=50.0,
            policy=policy,
        )


def test_executor_rejection_does_not_consume_approval(
    empty_queue: dict,
    portfolio: dict,
    proposal: dict,
    gate_result: dict,
    policy: dict,
) -> None:
    """A failed execution should leave approval available."""

    queued, request = create_request(
        empty_queue,
        proposal,
        gate_result,
    )
    approved_queue, approved = approve_request(
        queued,
        request["approval_id"],
    )

    updated_queue, updated_portfolio, result = (
        process_approved_trade(
            queue=approved_queue,
            portfolio=portfolio,
            approval_id=request["approval_id"],
            execution_price=0,
            policy=policy,
        )
    )

    assert approved["status"] == APPROVED
    assert result["execution_status"] == REJECTED
    assert result["portfolio_updated"] is False
    assert result["approval_consumed"] is False
    assert updated_queue == approved_queue
    assert updated_portfolio == portfolio
    assert updated_queue["requests"][0]["status"] == APPROVED


def test_consumed_approval_cannot_execute_twice(
    empty_queue: dict,
    portfolio: dict,
    proposal: dict,
    gate_result: dict,
    policy: dict,
) -> None:
    """One approval must authorize no more than one trade."""

    queued, request = create_request(
        empty_queue,
        proposal,
        gate_result,
    )
    approved_queue, _ = approve_request(
        queued,
        request["approval_id"],
    )

    consumed_queue, updated_portfolio, result = (
        process_approved_trade(
            queue=approved_queue,
            portfolio=portfolio,
            approval_id=request["approval_id"],
            execution_price=50.0,
            policy=policy,
        )
    )

    assert result["execution_status"] == EXECUTED

    with pytest.raises(
        ValueError,
        match="not approved",
    ):
        process_approved_trade(
            queue=consumed_queue,
            portfolio=updated_portfolio,
            approval_id=request["approval_id"],
            execution_price=50.0,
            policy=policy,
        )


def test_unknown_approval_id_is_rejected(
    empty_queue: dict,
    portfolio: dict,
    policy: dict,
) -> None:
    """An unknown identifier must not execute anything."""

    with pytest.raises(
        ValueError,
        match="not found",
    ):
        process_approved_trade(
            queue=empty_queue,
            portfolio=portfolio,
            approval_id="unknown-approval",
            execution_price=50.0,
            policy=policy,
        )