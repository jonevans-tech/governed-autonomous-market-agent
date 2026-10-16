"""Tests for the human approval review console."""

import copy

from src.approval_queue import (
    APPROVED,
    PENDING,
    REJECTED,
    submit_approval_request,
)
from src import review_approvals
from src.review_approvals import (
    build_argument_parser,
    get_pending_requests,
    print_pending_requests,
    review_and_save,
)


def create_pending_queue() -> tuple[dict, dict]:
    """Create a queue containing one pending request."""

    queue = {
        "schema_version": "1.0",
        "queue_type": "human_trade_approval",
        "requests": [],
    }

    proposal = {
        "action_type": "manage_virtual_portfolio",
        "symbol": "MED",
        "order_side": "BUY",
        "trade_value": 2500.0,
        "position_percentage": 2.5,
        "uses_real_money": False,
        "requires_human_approval": True,
        "source_decision": "BUY",
    }

    gate_result = {
        "action_type": "manage_virtual_portfolio",
        "governance_result": "REQUIRE_APPROVAL",
        "reason": (
            "The originating decision requires human approval."
        ),
        "policy_version": "1.0",
        "executed": False,
    }

    return submit_approval_request(
        queue=queue,
        proposal=proposal,
        gate_result=gate_result,
    )


def test_empty_queue_has_no_pending_requests() -> None:
    """An empty queue should return an empty list."""

    queue = {
        "requests": [],
    }

    assert get_pending_requests(queue) == []


def test_only_pending_requests_are_returned() -> None:
    """Reviewed requests should not appear as pending."""

    queue = {
        "requests": [
            {
                "approval_id": "pending-1",
                "status": PENDING,
            },
            {
                "approval_id": "approved-1",
                "status": APPROVED,
            },
            {
                "approval_id": "rejected-1",
                "status": REJECTED,
            },
        ],
    }

    pending = get_pending_requests(queue)

    assert len(pending) == 1
    assert pending[0]["approval_id"] == "pending-1"


def test_pending_results_do_not_mutate_queue() -> None:
    """Returned requests should be safe copies."""

    queue, _ = create_pending_queue()
    original = copy.deepcopy(queue)

    pending = get_pending_requests(queue)
    pending[0]["status"] = "CHANGED"

    assert queue == original


def test_empty_pending_list_prints_message(
    capsys,
) -> None:
    """The console should clearly report an empty queue."""

    print_pending_requests(
        {
            "requests": [],
        }
    )

    output = capsys.readouterr().out

    assert "No approval requests are pending." in output


def test_list_command_is_parsed() -> None:
    """The parser should recognize the list command."""

    parser = build_argument_parser()
    arguments = parser.parse_args(["list"])

    assert arguments.command == "list"


def test_approve_command_is_parsed() -> None:
    """The parser should collect approval details."""

    parser = build_argument_parser()
    arguments = parser.parse_args(
        [
            "approve",
            "--approval-id",
            "approval-123",
            "--reviewer",
            "Jon Evans",
            "--note",
            "Approved for simulation.",
        ]
    )

    assert arguments.command == "approve"
    assert arguments.approval_id == "approval-123"
    assert arguments.reviewer == "Jon Evans"
    assert arguments.note == "Approved for simulation."


def test_review_and_save_persists_approval(
    monkeypatch,
) -> None:
    """An approval decision should be saved."""

    queue, request = create_pending_queue()
    saved_state = {}

    monkeypatch.setattr(
        review_approvals,
        "load_approval_queue",
        lambda: copy.deepcopy(queue),
    )

    def capture_save(updated_queue):
        saved_state["queue"] = copy.deepcopy(
            updated_queue
        )

    monkeypatch.setattr(
        review_approvals,
        "save_approval_queue",
        capture_save,
    )

    reviewed = review_and_save(
        approval_id=request["approval_id"],
        decision="APPROVE",
        reviewer="Jon Evans",
        note="Approved for simulation.",
    )

    assert reviewed["status"] == APPROVED
    assert reviewed["reviewed_by"] == "Jon Evans"
    assert saved_state["queue"]["requests"][0][
        "status"
    ] == APPROVED


def test_review_and_save_persists_rejection(
    monkeypatch,
) -> None:
    """A rejection decision should be saved."""

    queue, request = create_pending_queue()
    saved_state = {}

    monkeypatch.setattr(
        review_approvals,
        "load_approval_queue",
        lambda: copy.deepcopy(queue),
    )

    def capture_save(updated_queue):
        saved_state["queue"] = copy.deepcopy(
            updated_queue
        )

    monkeypatch.setattr(
        review_approvals,
        "save_approval_queue",
        capture_save,
    )

    reviewed = review_and_save(
        approval_id=request["approval_id"],
        decision="REJECT",
        reviewer="Jon Evans",
        note="Declined.",
    )

    assert reviewed["status"] == REJECTED
    assert saved_state["queue"]["requests"][0][
        "status"
    ] == REJECTED