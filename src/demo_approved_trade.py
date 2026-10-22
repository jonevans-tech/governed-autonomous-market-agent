"""Prepare an end-to-end governed virtual-trade demonstration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.approval_queue import (
    create_proposal_hash,
    load_approval_queue,
    save_approval_queue,
    submit_approval_request,
)
from src.observe_market import (
    create_market_observation,
    load_market_history,
)
from src.policy_gate import evaluate_action


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEMO_STATE_PATH = (
    PROJECT_ROOT
    / "data"
    / "state"
    / "demo_approved_trade.json"
)

DEMO_SYMBOL = "MED"
DEMO_TRADE_VALUE = 2500.00


def find_latest_price(
    observation: dict[str, Any],
    symbol: str,
) -> float:
    """Return the latest simulated price for one symbol."""

    for asset in observation["assets"]:
        if asset["symbol"] == symbol:
            return float(asset["latest_price"])

    raise ValueError(
        f"The symbol {symbol} was not found in the observation."
    )


def build_demo_proposal() -> dict[str, Any]:
    """Create a simulation-only BUY proposal."""

    return {
        "action_type": "manage_virtual_portfolio",
        "symbol": DEMO_SYMBOL,
        "order_side": "BUY",
        "trade_value": DEMO_TRADE_VALUE,
        "position_percentage": 2.5,
        "uses_real_money": False,
        "requires_human_approval": True,
        "source_decision": "BUY",
    }


def find_existing_pending_request(
    queue: dict[str, Any],
    proposal: dict[str, Any],
) -> dict[str, Any] | None:
    """Find a matching pending request, if one exists."""

    proposal_hash = create_proposal_hash(proposal)

    for request in queue.get("requests", []):
        if (
            request.get("proposal_hash") == proposal_hash
            and request.get("status") == "PENDING"
        ):
            return request

    return None


def save_demo_state(
    request: dict[str, Any],
    execution_price: float,
) -> None:
    """Save the identifiers needed for the demonstration."""

    state = {
        "demo_type": "approved_virtual_trade",
        "simulation_only": True,
        "approval_id": request["approval_id"],
        "symbol": request["proposal"]["symbol"],
        "trade_value": request["proposal"]["trade_value"],
        "execution_price": execution_price,
        "approval_status": request["status"],
    }

    DEMO_STATE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with DEMO_STATE_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(state, file, indent=2)


def prepare_demo() -> dict[str, Any]:
    """Create or reuse one pending governed trade request."""

    market_rows = load_market_history()
    observation = create_market_observation(market_rows)

    execution_price = find_latest_price(
        observation,
        DEMO_SYMBOL,
    )

    proposal = build_demo_proposal()
    gate_result = evaluate_action(proposal)

    if gate_result["governance_result"] != "REQUIRE_APPROVAL":
        raise RuntimeError(
            "The policy gate did not require human approval."
        )

    queue = load_approval_queue()

    request = find_existing_pending_request(
        queue,
        proposal,
    )

    request_reused = request is not None

    if request is None:
        queue, request = submit_approval_request(
            queue=queue,
            proposal=proposal,
            gate_result=gate_result,
        )

        save_approval_queue(queue)

    save_demo_state(
        request=request,
        execution_price=execution_price,
    )

    return {
        "request": request,
        "gate_result": gate_result,
        "execution_price": execution_price,
        "request_reused": request_reused,
    }


def print_demo_result(
    result: dict[str, Any],
) -> None:
    """Display the prepared demonstration request."""

    request = result["request"]
    proposal = request["proposal"]

    print("Aureus approved-trade demonstration")
    print("===================================")
    print(f"Approval ID: {request['approval_id']}")
    print(f"Status: {request['status']}")
    print(
        "Policy gate: "
        f"{result['gate_result']['governance_result']}"
    )
    print(f"Symbol: {proposal['symbol']}")
    print(
        "Virtual trade value: "
        f"${proposal['trade_value']:,.2f}"
    )
    print(
        "Simulated execution price: "
        f"${result['execution_price']:,.2f}"
    )
    print(
        "Existing request reused: "
        f"{result['request_reused']}"
    )
    print()
    print("No trade has been executed.")
    print("Human approval is still required.")
    print(f"Demo state saved to: {DEMO_STATE_PATH}")


def main() -> None:
    """Prepare the governed trade demonstration."""

    result = prepare_demo()
    print_demo_result(result)


if __name__ == "__main__":
    main()