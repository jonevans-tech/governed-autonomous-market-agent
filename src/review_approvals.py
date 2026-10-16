"""Human command-line console for reviewing Aureus approvals."""

from __future__ import annotations

import argparse
import copy
from typing import Any

from src.approval_queue import (
    PENDING,
    load_approval_queue,
    review_approval_request,
    save_approval_queue,
)


def get_pending_requests(
    queue: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return safe copies of all pending requests."""

    requests = queue.get("requests")

    if not isinstance(requests, list):
        raise ValueError(
            "The approval request collection is malformed."
        )

    return [
        copy.deepcopy(request)
        for request in requests
        if request.get("status") == PENDING
    ]


def print_pending_requests(
    queue: dict[str, Any],
) -> None:
    """Display requests awaiting human review."""

    pending_requests = get_pending_requests(queue)

    print("Aureus pending approval requests")
    print("================================")

    if not pending_requests:
        print("No approval requests are pending.")
        return

    for request in pending_requests:
        proposal = request["proposal"]

        print()
        print(
            "Approval ID: "
            f"{request['approval_id']}"
        )
        print(
            "Created: "
            f"{request['created_at']}"
        )
        print(
            "Action: "
            f"{proposal['order_side']} "
            f"{proposal['symbol']}"
        )
        print(
            "Virtual amount: "
            f"${proposal['trade_value']:,.2f}"
        )
        print(
            "Real money: "
            f"{proposal['uses_real_money']}"
        )
        print(
            "Gate result: "
            f"{request['gate_result']['governance_result']}"
        )
        print(
            "Proposal fingerprint: "
            f"{request['proposal_hash']}"
        )


def review_and_save(
    approval_id: str,
    decision: str,
    reviewer: str,
    note: str = "",
) -> dict[str, Any]:
    """Review one request and persist the decision."""

    queue = load_approval_queue()

    updated_queue, reviewed_request = (
        review_approval_request(
            queue=queue,
            approval_id=approval_id,
            decision=decision,
            reviewed_by=reviewer,
            review_note=note,
        )
    )

    save_approval_queue(updated_queue)

    return reviewed_request


def print_review_result(
    reviewed_request: dict[str, Any],
) -> None:
    """Display the completed human review."""

    proposal = reviewed_request["proposal"]

    print("Aureus approval review")
    print("======================")
    print(
        "Approval ID: "
        f"{reviewed_request['approval_id']}"
    )
    print(
        "Decision: "
        f"{reviewed_request['review_decision']}"
    )
    print(
        "Status: "
        f"{reviewed_request['status']}"
    )
    print(
        "Reviewed by: "
        f"{reviewed_request['reviewed_by']}"
    )
    print(
        "Trade: "
        f"{proposal['order_side']} "
        f"{proposal['symbol']} "
        f"for ${proposal['trade_value']:,.2f}"
    )
    print()
    print("This decision applies to simulated activity only.")


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Review Aureus simulated trade approvals."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "list",
        help="List pending approval requests.",
    )

    approve_parser = subparsers.add_parser(
        "approve",
        help="Approve one pending request.",
    )
    approve_parser.add_argument(
        "--approval-id",
        required=True,
        help="Approval request identifier.",
    )
    approve_parser.add_argument(
        "--reviewer",
        required=True,
        help="Name of the human reviewer.",
    )
    approve_parser.add_argument(
        "--note",
        default="",
        help="Optional approval note.",
    )

    reject_parser = subparsers.add_parser(
        "reject",
        help="Reject one pending request.",
    )
    reject_parser.add_argument(
        "--approval-id",
        required=True,
        help="Approval request identifier.",
    )
    reject_parser.add_argument(
        "--reviewer",
        required=True,
        help="Name of the human reviewer.",
    )
    reject_parser.add_argument(
        "--note",
        default="",
        help="Optional rejection note.",
    )

    return parser


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = build_argument_parser()
    return parser.parse_args()


def main() -> None:
    """Run the human approval console."""

    arguments = parse_arguments()

    if arguments.command == "list":
        queue = load_approval_queue()
        print_pending_requests(queue)
        return

    if arguments.command == "approve":
        decision = "APPROVE"
    else:
        decision = "REJECT"

    reviewed_request = review_and_save(
        approval_id=arguments.approval_id,
        decision=decision,
        reviewer=arguments.reviewer,
        note=arguments.note,
    )

    print_review_result(reviewed_request)


if __name__ == "__main__":
    main()