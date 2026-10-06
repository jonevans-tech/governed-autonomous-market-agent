import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config_loader import load_policy
from src.observe_market import (
    create_market_observation,
    load_market_history,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_PATH = (
    PROJECT_ROOT
    / "data"
    / "state"
    / "virtual_portfolio.json"
)


def current_utc_timestamp() -> str:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def create_virtual_portfolio(
    starting_cash: float,
) -> dict[str, Any]:
    """Create a new simulated investment portfolio."""
    timestamp = current_utc_timestamp()

    return {
        "schema_version": "1.0",
        "portfolio_type": "simulation_only",
        "currency": "USD",
        "starting_cash": round(starting_cash, 2),
        "cash_balance": round(starting_cash, 2),
        "positions": {},
        "transactions": [],
        "invested_market_value": 0.00,
        "total_portfolio_value": round(
            starting_cash,
            2,
        ),
        "total_unrealized_gain_loss": 0.00,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def load_portfolio(
    file_path: Path = PORTFOLIO_PATH,
) -> dict[str, Any]:
    """Load the portfolio or create a new one."""
    if file_path.exists():
        with file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    policy = load_policy()
    starting_cash = policy["financial_limits"][
        "starting_virtual_cash"
    ]

    return create_virtual_portfolio(
        starting_cash
    )


def save_portfolio(
    portfolio: dict[str, Any],
    file_path: Path = PORTFOLIO_PATH,
) -> None:
    """Save the current simulated portfolio."""
    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(portfolio, file, indent=2)


def build_latest_price_map(
    observation: dict[str, Any],
) -> dict[str, float]:
    """Build a symbol-to-price lookup."""
    return {
        asset["symbol"]: asset["latest_price"]
        for asset in observation["assets"]
    }


def mark_portfolio_to_market(
    portfolio: dict[str, Any],
    latest_prices: dict[str, float],
) -> dict[str, Any]:
    """Update every position using current prices."""
    updated_portfolio = copy.deepcopy(portfolio)

    invested_market_value = 0.00
    total_unrealized_gain_loss = 0.00

    for symbol, position in updated_portfolio[
        "positions"
    ].items():
        if symbol not in latest_prices:
            raise ValueError(
                f"Current price not found for {symbol}"
            )

        current_price = latest_prices[symbol]
        quantity = position["quantity"]
        average_cost = position["average_cost"]

        market_value = round(
            quantity * current_price,
            2,
        )
        cost_basis = round(
            quantity * average_cost,
            2,
        )
        unrealized_gain_loss = round(
            market_value - cost_basis,
            2,
        )

        position["current_price"] = current_price
        position["market_value"] = market_value
        position["cost_basis"] = cost_basis
        position["unrealized_gain_loss"] = (
            unrealized_gain_loss
        )

        invested_market_value += market_value
        total_unrealized_gain_loss += (
            unrealized_gain_loss
        )

    updated_portfolio["invested_market_value"] = round(
        invested_market_value,
        2,
    )
    updated_portfolio[
        "total_unrealized_gain_loss"
    ] = round(
        total_unrealized_gain_loss,
        2,
    )
    updated_portfolio["total_portfolio_value"] = round(
        updated_portfolio["cash_balance"]
        + invested_market_value,
        2,
    )
    updated_portfolio["updated_at"] = (
        current_utc_timestamp()
    )

    return updated_portfolio


def print_portfolio_summary(
    portfolio: dict[str, Any],
) -> None:
    """Display a readable portfolio summary."""
    print("Aureus virtual portfolio")
    print("=========================")
    print(
        f"Cash balance: "
        f"${portfolio['cash_balance']:,.2f}"
    )
    print(
        "Invested market value: "
        f"${portfolio['invested_market_value']:,.2f}"
    )
    print(
        "Total portfolio value: "
        f"${portfolio['total_portfolio_value']:,.2f}"
    )
    print(
        "Unrealized gain or loss: "
        f"${portfolio['total_unrealized_gain_loss']:,.2f}"
    )
    print(
        f"Open positions: "
        f"{len(portfolio['positions'])}"
    )
    print(
        f"Transactions: "
        f"{len(portfolio['transactions'])}"
    )


def main() -> None:
    portfolio = load_portfolio()

    market_rows = load_market_history()
    observation = create_market_observation(
        market_rows
    )
    latest_prices = build_latest_price_map(
        observation
    )

    portfolio = mark_portfolio_to_market(
        portfolio,
        latest_prices,
    )
    save_portfolio(portfolio)
    print_portfolio_summary(portfolio)

    print()
    print(f"Portfolio saved to: {PORTFOLIO_PATH}")


if __name__ == "__main__":
    main()
