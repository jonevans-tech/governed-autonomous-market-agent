import pytest

from src.portfolio import (
    build_latest_price_map,
    create_virtual_portfolio,
    load_portfolio,
    mark_portfolio_to_market,
    save_portfolio,
)
from src.observe_market import (
    create_market_observation,
    load_market_history,
)


def create_portfolio_with_position():
    portfolio = create_virtual_portfolio(
        100000.00
    )
    portfolio["cash_balance"] = 99000.00
    portfolio["positions"]["TST"] = {
        "symbol": "TST",
        "company_name": "Test Company",
        "quantity": 10.0,
        "average_cost": 100.00,
        "current_price": 100.00,
        "market_value": 1000.00,
        "cost_basis": 1000.00,
        "unrealized_gain_loss": 0.00,
    }

    return portfolio


def test_new_portfolio_starts_with_cash_only():
    portfolio = create_virtual_portfolio(
        100000.00
    )

    assert portfolio["cash_balance"] == 100000.00
    assert portfolio["positions"] == {}
    assert portfolio["transactions"] == []
    assert portfolio["total_portfolio_value"] == (
        100000.00
    )


def test_missing_portfolio_uses_policy_cash(
    tmp_path,
):
    portfolio_path = tmp_path / "portfolio.json"

    portfolio = load_portfolio(portfolio_path)

    assert portfolio["starting_cash"] == 100000.00
    assert portfolio["portfolio_type"] == (
        "simulation_only"
    )


def test_latest_price_map_contains_four_assets():
    observation = create_market_observation(
        load_market_history()
    )

    price_map = build_latest_price_map(
        observation
    )

    assert set(price_map) == {
        "AUR",
        "GRD",
        "HBR",
        "MED",
    }
    assert price_map["AUR"] == 112.76


def test_empty_portfolio_value_remains_cash():
    portfolio = create_virtual_portfolio(
        100000.00
    )

    updated = mark_portfolio_to_market(
        portfolio,
        {},
    )

    assert updated["cash_balance"] == 100000.00
    assert updated["invested_market_value"] == 0.00
    assert updated["total_portfolio_value"] == (
        100000.00
    )


def test_position_is_marked_to_current_price():
    portfolio = create_portfolio_with_position()

    updated = mark_portfolio_to_market(
        portfolio,
        {"TST": 110.00},
    )
    position = updated["positions"]["TST"]

    assert position["market_value"] == 1100.00
    assert position["cost_basis"] == 1000.00
    assert position["unrealized_gain_loss"] == 100.00


def test_total_value_includes_cash_and_positions():
    portfolio = create_portfolio_with_position()

    updated = mark_portfolio_to_market(
        portfolio,
        {"TST": 110.00},
    )

    assert updated["invested_market_value"] == 1100.00
    assert updated["total_portfolio_value"] == (
        100100.00
    )
    assert updated[
        "total_unrealized_gain_loss"
    ] == 100.00


def test_missing_position_price_raises_error():
    portfolio = create_portfolio_with_position()

    with pytest.raises(
        ValueError,
        match="Current price not found",
    ):
        mark_portfolio_to_market(
            portfolio,
            {},
        )


def test_portfolio_can_be_saved_and_loaded(
    tmp_path,
):
    portfolio_path = tmp_path / "portfolio.json"
    portfolio = create_portfolio_with_position()

    save_portfolio(portfolio, portfolio_path)
    loaded_portfolio = load_portfolio(
        portfolio_path
    )

    assert loaded_portfolio == portfolio
