import pytest

from src.demo_approved_trade import (
    build_demo_proposal,
    find_existing_pending_request,
    find_latest_price,
)
from src.approval_queue import create_proposal_hash


def make_observation():
    return {
        "assets": [
            {
                "symbol": "MED",
                "latest_price": 66.54,
            },
            {
                "symbol": "TST",
                "latest_price": 50.00,
            },
        ]
    }


def test_demo_proposal_is_simulation_only():
    proposal = build_demo_proposal()

    assert proposal["action_type"] == (
        "manage_virtual_portfolio"
    )
    assert proposal["symbol"] == "MED"
    assert proposal["order_side"] == "BUY"
    assert proposal["trade_value"] == 2500.00
    assert proposal["uses_real_money"] is False


def test_demo_proposal_requires_human_approval():
    proposal = build_demo_proposal()

    assert proposal["requires_human_approval"] is True


def test_latest_demo_price_is_found():
    price = find_latest_price(
        make_observation(),
        "MED",
    )

    assert price == 66.54


def test_unknown_symbol_raises_error():
    with pytest.raises(
        ValueError,
        match="was not found",
    ):
        find_latest_price(
            make_observation(),
            "UNKNOWN",
        )


def test_matching_pending_request_is_found():
    proposal = build_demo_proposal()

    request = {
        "approval_id": "approval-123",
        "status": "PENDING",
        "proposal_hash": create_proposal_hash(proposal),
        "proposal": proposal,
    }

    queue = {
        "requests": [request],
    }

    result = find_existing_pending_request(
        queue,
        proposal,
    )

    assert result == request


def test_consumed_request_is_not_reused():
    proposal = build_demo_proposal()

    request = {
        "approval_id": "approval-123",
        "status": "CONSUMED",
        "proposal_hash": create_proposal_hash(proposal),
        "proposal": proposal,
    }

    queue = {
        "requests": [request],
    }

    result = find_existing_pending_request(
        queue,
        proposal,
    )

    assert result is None