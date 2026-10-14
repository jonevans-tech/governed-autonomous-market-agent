"""Persistent human-approval queue for simulated trades."""

from __future__ import annotations

import copy
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APPROVAL_QUEUE_PATH = (
    PROJECT_ROOT
    / "data"
    / "state"
    / "approval_queue.json"
)

PENDING = "PENDING"
APPROVED = "APPROVED"
REJECTED = "REJECTED"
CONSUMED = "CONSUMED"

VALID_REVIEW_DECISIONS = {
    "APPROVE",
    "REJECT",
}


def current_utc_timestamp() -> str:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


def create_empty_queue() -> dict[str, Any]:
    """Create an empty human-approval queue."""

    return {
        "schema_version": "1.0",
        "queue_type": "human_trade_approval",
        "requests": [],
    }


def load_approval_queue(
    file_path: Path = APPROVAL_QUEUE_PATH,
) -> dict[str, Any]:
    """Load the approval queue or create an empty one."""

    if not file_path.exists():
        return create_empty_queue()

    with file_path.open("r", encoding="utf-8") as file:
        queue = json.load(file)

    if not isinstance(queue, dict):
        raise ValueError("The approval queue is malformed.")

    if not isinstance(queue.get("requests"), list):
        raise ValueError(
            "The approval request collection is malformed."
        )

    return queue


def save_approval_queue(
    queue: dict[str, Any],
    file_path: Path = APPROVAL_QUEUE_PATH,
) -> None:
    """Save the approval queue as persistent runtime state."""

    if not isinstance(queue, dict):
        raise ValueError("The approval queue is malformed.")

    if not isinstance(queue.get("requests"), list):
        raise ValueError(
            "The approval request collection is malformed."
        )

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(queue, file, indent=2)


def create_proposal_hash(
    proposal: dict[str, Any],
) -> str:
    """Create a stable fingerprint for a trade proposal."""

    if not isinstance(proposal, dict):
        raise ValueError("The trade proposal is malformed.")

    serialized = json.dumps(
        proposal,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def validate_trade_proposal(
    proposal: dict[str, Any],
) -> None:
    """Validate a proposal before requesting approval."""

    if not isinstance(proposal, dict):
        raise ValueError("The trade proposal is malformed.")

    if (
        proposal.get("action_type")
        != "manage_virtual_portfolio"
    ):
        raise ValueError(
            "Only virtual portfolio proposals may be submitted."
        )

    if proposal.get("order_side") != "BUY":
        raise ValueError(
            "Only simulated BUY proposals are currently supported."
        )

    if proposal.get("uses_real_money") is not False:
        raise ValueError(
            "Real-money proposals cannot enter the queue."
        )

    symbol = proposal.get("symbol")

    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError(
            "The proposal requires a valid symbol."
        )

    trade_value = proposal.get("trade_value")

    if (
        not isinstance(trade_value, (int, float))
        or isinstance(trade_value, bool)
        or trade_value <= 0
    ):
        raise ValueError(
            "The proposal requires a positive trade value."
        )


def validate_gate_result(
    gate_result: dict[str, Any],
) -> None:
    """Validate governance metadata for an approval request."""

    if not isinstance(gate_result, dict):
        raise ValueError(
            "The policy-gate result is malformed."
        )

    if (
        gate_result.get("action_type")
        != "manage_virtual_portfolio"
    ):
        raise ValueError(
            "The gate result does not describe a virtual trade."
        )

    if (
        gate_result.get("governance_result")
        != "REQUIRE_APPROVAL"
    ):
        raise ValueError(
            "Only approval-required actions belong in the queue."
        )

    if gate_result.get("executed") is not False:
        raise ValueError(
            "An already-executed action cannot request approval."
        )


def find_request(
    queue: dict[str, Any],
    approval_id: str,
) -> dict[str, Any] | None:
    """Find one approval request by its identifier."""

    for request in queue.get("requests", []):
        if request.get("approval_id") == approval_id:
            return request

    return None


def submit_approval_request(
    queue: dict[str, Any],
    proposal: dict[str, Any],
    gate_result: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Add a governed trade proposal to the approval queue."""

    validate_trade_proposal(proposal)
    validate_gate_result(gate_result)

    proposal_hash = create_proposal_hash(proposal)

    for existing_request in queue.get("requests", []):
        if (
            existing_request.get("proposal_hash")
            == proposal_hash
            and existing_request.get("status")
            == PENDING
        ):
            raise ValueError(
                "This proposal already has a pending request."
            )

    request = {
        "approval_id": str(uuid.uuid4()),
        "created_at": current_utc_timestamp(),
        "status": PENDING,
        "proposal_hash": proposal_hash,
        "proposal": copy.deepcopy(proposal),
        "gate_result": copy.deepcopy(gate_result),
        "reviewed_at": None,
        "reviewed_by": None,
        "review_decision": None,
        "review_note": None,
        "consumed_at": None,
        "transaction_id": None,
    }

    updated_queue = copy.deepcopy(queue)
    updated_queue.setdefault(
        "requests",
        [],
    ).append(request)

    return updated_queue, copy.deepcopy(request)


def review_approval_request(
    queue: dict[str, Any],
    approval_id: str,
    decision: str,
    reviewed_by: str,
    review_note: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Approve or reject one pending request."""

    if decision not in VALID_REVIEW_DECISIONS:
        raise ValueError(
            "The review decision must be APPROVE or REJECT."
        )

    if (
        not isinstance(reviewed_by, str)
        or not reviewed_by.strip()
    ):
        raise ValueError(
            "The reviewer name is required."
        )

    updated_queue = copy.deepcopy(queue)
    request = find_request(
        updated_queue,
        approval_id,
    )

    if request is None:
        raise ValueError(
            "The approval request was not found."
        )

    if request.get("status") != PENDING:
        raise ValueError(
            "Only pending requests can be reviewed."
        )

    request["reviewed_at"] = current_utc_timestamp()
    request["reviewed_by"] = reviewed_by.strip()
    request["review_decision"] = decision
    request["review_note"] = review_note

    if decision == "APPROVE":
        request["status"] = APPROVED
    else:
        request["status"] = REJECTED

    return updated_queue, copy.deepcopy(request)


def build_approval_record(
    queue: dict[str, Any],
    approval_id: str,
) -> dict[str, Any]:
    """Build an executor approval record from an approved request."""

    request = find_request(
        queue,
        approval_id,
    )

    if request is None:
        raise ValueError(
            "The approval request was not found."
        )

    if request.get("status") != APPROVED:
        raise ValueError(
            "The approval request is not approved."
        )

    proposal = request["proposal"]

    if (
        create_proposal_hash(proposal)
        != request.get("proposal_hash")
    ):
        raise ValueError(
            "The approved proposal has been modified."
        )

    return {
        "approval_id": request["approval_id"],
        "approved": True,
        "approved_by": request["reviewed_by"],
        "approved_at": request["reviewed_at"],
        "symbol": proposal["symbol"],
        "proposal_hash": request["proposal_hash"],
    }


def consume_approval(
    queue: dict[str, Any],
    approval_id: str,
    transaction_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Mark an approved request as used by one transaction."""

    if (
        not isinstance(transaction_id, str)
        or not transaction_id.strip()
    ):
        raise ValueError(
            "A valid transaction identifier is required."
        )

    updated_queue = copy.deepcopy(queue)
    request = find_request(
        updated_queue,
        approval_id,
    )

    if request is None:
        raise ValueError(
            "The approval request was not found."
        )

    if request.get("status") != APPROVED:
        raise ValueError(
            "Only an approved request can be consumed."
        )

    request["status"] = CONSUMED
    request["consumed_at"] = current_utc_timestamp()
    request["transaction_id"] = transaction_id.strip()

    return updated_queue, copy.deepcopy(request)


def summarize_queue(
    queue: dict[str, Any],
) -> dict[str, int]:
    """Count requests by approval status."""

    summary = {
        PENDING: 0,
        APPROVED: 0,
        REJECTED: 0,
        CONSUMED: 0,
    }

    for request in queue.get("requests", []):
        status = request.get("status")

        if status in summary:
            summary[status] += 1

    return summary


def print_queue_summary(
    queue: dict[str, Any],
) -> None:
    """Display the current human-approval queue."""

    summary = summarize_queue(queue)

    print("Aureus human approval queue")
    print("===========================")
    print(f"Pending requests: {summary[PENDING]}")
    print(f"Approved requests: {summary[APPROVED]}")
    print(f"Rejected requests: {summary[REJECTED]}")
    print(f"Consumed approvals: {summary[CONSUMED]}")


def main() -> None:
    """Load and display the current approval queue."""

    queue = load_approval_queue()
    save_approval_queue(queue)
    print_queue_summary(queue)
    print()
    print(f"Approval queue saved to: {APPROVAL_QUEUE_PATH}")


if __name__ == "__main__":
    main()