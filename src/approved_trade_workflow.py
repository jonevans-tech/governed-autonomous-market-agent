"""Execute approved simulated trades through one governed workflow."""

from __future__ import annotations

import argparse
import copy
from typing import Any

from src.approval_queue import (
    build_approval_record,
    consume_approval,
    find_request,
    load_approval_queue,
    save_approval_queue,
)
from src.config_loader import load_policy
from src.portfolio import (
    load_portfolio,
    save_portfolio,
)
from src.trade_executor import (
    EXECUTED,
    execute_virtual_buy,
)


def process_approved_trade(
    queue: dict[str, Any],
    portfolio: dict[str, Any],
    approval_id: str,
    execution_price: float,
    policy: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    """Process one approved simulated trade in memory."""

    original_queue = copy.deepcopy(queue)
    original_portfolio = copy.deepcopy(portfolio)

    if (
        not isinstance(approval_id, str)
        or not approval_id.strip()
    ):
        raise ValueError(
            "A valid approval identifier is required."
        )

    request = find_request(
        queue,
        approval_id.strip(),
    )

    if request is None:
        raise ValueError(
            "The approval request was not found."
        )

    approval_record = build_approval_record(
        queue,
        approval_id.strip(),
    )

    proposal = copy.deepcopy(
        request["proposal"]
    )
    gate_result = copy.deepcopy(
        request["gate_result"]
    )

    updated_portfolio, execution_result = (
        execute_virtual_buy(
            portfolio=portfolio,
            proposal=proposal,
            gate_result=gate_result,
            approval_record=approval_record,
            execution_price=execution_price,
            policy=policy,
        )
    )

    if execution_result["execution_status"] != EXECUTED:
        workflow_result = copy.deepcopy(
            execution_result
        )
        workflow_result["approval_id"] = approval_id
        workflow_result["approval_consumed"] = False

        return (
            original_queue,
            original_portfolio,
            workflow_result,
        )

    transaction = execution_result["transaction"]
    transaction_id = transaction["transaction_id"]

    updated_queue, consumed_request = consume_approval(
        queue=queue,
        approval_id=approval_id.strip(),
        transaction_id=transaction_id,
    )

    workflow_result = copy.deepcopy(
        execution_result
    )
    workflow_result["approval_id"] = approval_id.strip()
    workflow_result["approval_consumed"] = True
    workflow_result["approval_status"] = (
        consumed_request["status"]
    )

    return (
        updated_queue,
        updated_portfolio,
        workflow_result,
    )


def execute_persisted_approved_trade(
    approval_id: str,
    execution_price: float,
) -> dict[str, Any]:
    """Execute one approved trade using persistent state."""

    queue = load_approval_queue()
    portfolio = load_portfolio()
    policy = load_policy()

    (
        updated_queue,
        updated_portfolio,
        result,
    ) = process_approved_trade(
        queue=queue,
        portfolio=portfolio,
        approval_id=approval_id,
        execution_price=execution_price,
        policy=policy,
    )

    if result["execution_status"] == EXECUTED:
        save_portfolio(updated_portfolio)
        save_approval_queue(updated_queue)

    return result


def print_workflow_result(
    result: dict[str, Any],
) -> None:
    """Display the approved-trade workflow result."""

    print("Aureus approved trade workflow")
    print("==============================")
    print(
        "Execution status: "
        f"{result['execution_status']}"
    )
    print(f"Reason: {result['reason']}")
    print(
        "Portfolio updated: "
        f"{result['portfolio_updated']}"
    )
    print(
        "Approval consumed: "
        f"{result.get('approval_consumed', False)}"
    )

    transaction = result.get("transaction")

    if transaction is not None:
        print(
            "Transaction ID: "
            f"{transaction['transaction_id']}"
        )
        print(
            "Virtual trade: "
            f"{transaction['order_side']} "
            f"{transaction['symbol']} "
            f"for ${transaction['trade_value']:,.2f}"
        )

    print()
    print("This workflow uses simulated funds only.")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Execute an approved simulated Aureus trade."
        )
    )

    parser.add_argument(
        "--approval-id",
        required=True,
        help="Approval request identifier.",
    )

    parser.add_argument(
        "--price",
        required=True,
        type=float,
        help="Simulated execution price.",
    )

    return parser.parse_args()


def main() -> None:
    """Run one approved simulated trade."""

    arguments = parse_arguments()

    result = execute_persisted_approved_trade(
        approval_id=arguments.approval_id,
        execution_price=arguments.price,
    )

    print_workflow_result(result)


if __name__ == "__main__":
    main()