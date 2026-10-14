"""Tests for the persistent human-approval queue."""

import copy
import json

import pytest

from src.approval_queue import (
    APPROVED,
    CONSUMED,
    PENDING,
    REJECTED,
    build_approval_record,
    consume_approval,
    create_empty_queue,
    create_proposal_hash,
    load_approval_queue,
    review_approval_request,
    save_approval_queue,
    submit_approval_request,
    summarize_queue,
)


@pytest.fixture
def queue() -> dict:
    """Return an empty approval queue."""
    return create_empty_queue()


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
    """Return a gate result requiring approval."""
    return {
        "action_type": "manage_virtual_portfolio",
        "governance_result": "REQUIRE_APPROVAL",
        "reason": (
            "The originating decision requires human approval."
        ),
        "policy_version": "1.0",
        "executed": False,
    }


def create_pending_request(
    queue: dict,
    proposal: dict,
    gate_result: dict,
) -> tuple[dict, dict]:
    """Submit one valid request for use by tests."""

    return submit_approval_request(
        queue=queue,
        proposal=proposal,
        gate_result=gate_result,
    )


def test_empty_queue_has_no_requests() -> None:
    """A new queue should begin empty."""

    queue = create_empty_queue()

    assert queue["queue_type"] == "human_trade_approval"
    assert queue["requests"] == []


def test_missing_queue_file_returns_empty_queue(
    tmp_path,
) -> None:
    """A missing runtime file should not cause failure."""

    queue = load_approval_queue(
        tmp_path / "missing.json"
    )

    assert queue["requests"] == []


def test_queue_can_be_saved_and_loaded(
    tmp_path,
    queue: dict,
) -> None:
    """Queue state should persist as JSON."""

    file_path = tmp_path / "approval_queue.json"

    save_approval_queue(queue, file_path)
    loaded = load_approval_queue(file_path)

    assert loaded == queue


def test_proposal_hash_is_stable() -> None:
    """Dictionary key order must not change the hash."""

    first = {
        "symbol": "MED",
        "trade_value": 2500.0,
    }
    second = {
        "trade_value": 2500.0,
        "symbol": "MED",
    }

    assert create_proposal_hash(first) == (
        create_proposal_hash(second)
    )


def test_valid_proposal_becomes_pending_request(
    queue: dict,
    proposal: dict,
    gate_result: dict,
) -> None:
    """A governed BUY should enter the queue as pending."""

    updated, request = create_pending_request(
        queue,
        proposal,
        gate_result,
    )

    assert request["status"] == PENDING
    assert request["proposal"]["symbol"] == "MED"
    assert len(updated["requests"]) == 1
    assert queue["requests"] == []


def test_real_money_proposal_is_rejected(
    queue: dict,
    proposal: dict,
    gate_result: dict,
) -> None:
    """Real-money proposals must never enter the queue."""

    proposal["uses_real_money"] = True

    with pytest.raises(
        ValueError,
        match="Real-money",
    ):
        submit_approval_request(
            queue,
            proposal,
            gate_result,
        )


def test_duplicate_pending_proposal_is_rejected(
    queue: dict,
    proposal: dict,
    gate_result: dict,
) -> None:
    """The same proposal cannot be pending twice."""

    updated, _ = create_pending_request(
        queue,
        proposal,
        gate_result,
    )

    with pytest.raises(
        ValueError,
        match="already has a pending request",
    ):
        submit_approval_request(
            updated,
            proposal,
            gate_result,
        )


def test_pending_request_can_be_approved(
    queue: dict,
    proposal: dict,
    gate_result: dict,
) -> None:
    """A human reviewer can approve a pending request."""

    queued, request = create_pending_request(
        queue,
        proposal,
        gate_result,
    )

    reviewed_queue, reviewed = review_approval_request(
        queue=queued,
        approval_id=request["approval_id"],
        decision="APPROVE",
        reviewed_by="Jon Evans",
        review_note="Approved for simulation.",
    )

    assert reviewed["status"] == APPROVED
    assert reviewed["reviewed_by"] == "Jon Evans"
    assert reviewed_queue["requests"][0][
        "review_decision"
    ] == "APPROVE"


def test_pending_request_can_be_rejected(
    queue: dict,
    proposal: dict,
    gate_result: dict,
) -> None:
    """A human reviewer can reject a pending request."""

    queued, request = create_pending_request(
        queue,
        proposal,
        gate_result,
    )

    _, reviewed = review_approval_request(
        queue=queued,
        approval_id=request["approval_id"],
        decision="REJECT",
        reviewed_by="Jon Evans",
        review_note="Risk is too high.",
    )

    assert reviewed["status"] == REJECTED
    assert reviewed["review_decision"] == "REJECT"


def test_invalid_review_decision_is_rejected(
    queue: dict,
    proposal: dict,
    gate_result: dict,
) -> None:
    """Only APPROVE and REJECT are valid decisions."""

    queued, request = create_pending_request(
        queue,
        proposal,
        gate_result,
    )

    with pytest.raises(
        ValueError,
        match="APPROVE or REJECT",
    ):
        review_approval_request(
            queue=queued,
            approval_id=request["approval_id"],
            decision="MAYBE",
            reviewed_by="Jon Evans",
        )


def test_approved_request_builds_executor_record(
    queue: dict,
    proposal: dict,
    gate_result: dict,
) -> None:
    """An approved request should produce an approval record."""

    queued, request = create_pending_request(
        queue,
        proposal,
        gate_result,
    )

    approved_queue, _ = review_approval_request(
        queue=queued,
        approval_id=request["approval_id"],
        decision="APPROVE",
        reviewed_by="Jon Evans",
    )

    approval_record = build_approval_record(
        approved_queue,
        request["approval_id"],
    )

    assert approval_record["approved"] is True
    assert approval_record["approved_by"] == "Jon Evans"
    assert approval_record["symbol"] == "MED"


def test_modified_approved_proposal_is_detected(
    queue: dict,
    proposal: dict,
    gate_result: dict,
) -> None:
    """Changing a proposal after approval must invalidate it."""

    queued, request = create_pending_request(
        queue,
        proposal,
        gate_result,
    )

    approved_queue, _ = review_approval_request(
        queue=queued,
        approval_id=request["approval_id"],
        decision="APPROVE",
        reviewed_by="Jon Evans",
    )

    tampered_queue = copy.deepcopy(approved_queue)
    tampered_queue["requests"][0]["proposal"][
        "trade_value"
    ] = 5000.0

    with pytest.raises(
        ValueError,
        match="modified",
    ):
        build_approval_record(
            tampered_queue,
            request["approval_id"],
        )


def test_approval_can_be_consumed_once(
    queue: dict,
    proposal: dict,
    gate_result: dict,
) -> None:
    """An approved request becomes consumed after execution."""

    queued, request = create_pending_request(
        queue,
        proposal,
        gate_result,
    )

    approved_queue, _ = review_approval_request(
        queue=queued,
        approval_id=request["approval_id"],
        decision="APPROVE",
        reviewed_by="Jon Evans",
    )

    consumed_queue, consumed = consume_approval(
        queue=approved_queue,
        approval_id=request["approval_id"],
        transaction_id="transaction-123",
    )

    assert consumed["status"] == CONSUMED
    assert consumed["transaction_id"] == "transaction-123"

    with pytest.raises(
        ValueError,
        match="Only an approved request",
    ):
        consume_approval(
            queue=consumed_queue,
            approval_id=request["approval_id"],
            transaction_id="transaction-456",
        )


def test_queue_summary_counts_each_status() -> None:
    """The queue summary should count all statuses."""

    queue = create_empty_queue()
    queue["requests"] = [
        {"status": PENDING},
        {"status": APPROVED},
        {"status": REJECTED},
        {"status": CONSUMED},
    ]

    summary = summarize_queue(queue)

    assert summary[PENDING] == 1
    assert summary[APPROVED] == 1
    assert summary[REJECTED] == 1
    assert summary[CONSUMED] == 1