import pytest

from src.policy_gate import (
    ALLOW,
    BLOCK,
    REQUIRE_APPROVAL,
    evaluate_action,
)


def make_virtual_trade(
    trade_value=2500.00,
    position_percentage=5.0,
):
    return {
        "action_type": "manage_virtual_portfolio",
        "trade_value": trade_value,
        "position_percentage": position_percentage,
        "uses_real_money": False,
    }


def test_routine_virtual_trade_is_allowed():
    result = evaluate_action(make_virtual_trade())

    assert result["governance_result"] == ALLOW
    assert result["executed"] is False


def test_trade_at_exact_limit_is_allowed():
    proposal = make_virtual_trade(trade_value=5000.00)

    result = evaluate_action(proposal)

    assert result["governance_result"] == ALLOW


def test_trade_above_limit_requires_approval():
    proposal = make_virtual_trade(trade_value=5000.01)

    result = evaluate_action(proposal)

    assert result["governance_result"] == REQUIRE_APPROVAL


def test_position_above_limit_is_blocked():
    proposal = make_virtual_trade(
        trade_value=2500.00,
        position_percentage=20.01,
    )

    result = evaluate_action(proposal)

    assert result["governance_result"] == BLOCK
    assert "position" in result["reason"].lower()


def test_real_money_activity_is_blocked():
    proposal = make_virtual_trade()
    proposal["uses_real_money"] = True

    result = evaluate_action(proposal)

    assert result["governance_result"] == BLOCK
    assert "real-money" in result["reason"].lower()


def test_prohibited_wallet_access_is_blocked():
    proposal = {
        "action_type": "access_cryptocurrency_wallet",
    }

    result = evaluate_action(proposal)

    assert result["governance_result"] == BLOCK
    assert "prohibited" in result["reason"].lower()


def test_external_publication_requires_approval():
    proposal = {
        "action_type": "publish_external_content",
    }

    result = evaluate_action(proposal)

    assert result["governance_result"] == REQUIRE_APPROVAL


def test_unknown_action_is_blocked_by_default():
    proposal = {
        "action_type": "unknown_action",
    }

    result = evaluate_action(proposal)

    assert result["governance_result"] == BLOCK
    assert "default" in result["reason"].lower()


def test_missing_action_type_is_blocked():
    result = evaluate_action({})

    assert result["governance_result"] == BLOCK
    assert "action type" in result["reason"].lower()


@pytest.mark.parametrize(
    "invalid_trade_value",
    [None, "2500", 0],
)
def test_invalid_trade_values_are_blocked(
    invalid_trade_value,
):
    proposal = make_virtual_trade(
        trade_value=invalid_trade_value,
    )

    result = evaluate_action(proposal)

    assert result["governance_result"] == BLOCK
