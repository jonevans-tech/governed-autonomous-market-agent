import csv
import random
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MARKET_DATA_PATH = PROJECT_ROOT / "data" / "market" / "market_history.csv"

ASSETS = [
    {
        "symbol": "AUR",
        "company_name": "Aurora Systems",
        "sector": "AI Infrastructure",
        "starting_price": 120.00,
        "daily_drift": 0.35,
        "volatility": 1.80,
    },
    {
        "symbol": "GRD",
        "company_name": "GreenGrid Energy",
        "sector": "Clean Energy",
        "starting_price": 75.00,
        "daily_drift": 0.15,
        "volatility": 1.20,
    },
    {
        "symbol": "HBR",
        "company_name": "Harbor Financial",
        "sector": "Financial Services",
        "starting_price": 95.00,
        "daily_drift": 0.08,
        "volatility": 0.90,
    },
    {
        "symbol": "MED",
        "company_name": "Meridian Health",
        "sector": "Healthcare",
        "starting_price": 62.00,
        "daily_drift": 0.20,
        "volatility": 1.10,
    },
]


def generate_market_data(
    days: int = 30,
    seed: int = 42,
) -> list[dict]:
    """Generate reproducible fictional market history."""
    random_generator = random.Random(seed)
    start_date = date(2026, 1, 1)
    market_rows = []

    for asset in ASSETS:
        current_price = asset["starting_price"]

        for day_number in range(days):
            market_date = start_date + timedelta(days=day_number)

            daily_change_pct = random_generator.gauss(
                asset["daily_drift"],
                asset["volatility"],
            )

            current_price *= 1 + (daily_change_pct / 100)
            current_price = max(current_price, 1.00)

            volume = random_generator.randint(100_000, 1_500_000)
            sentiment_score = random_generator.uniform(-1.0, 1.0)

            market_rows.append(
                {
                    "date": market_date.isoformat(),
                    "symbol": asset["symbol"],
                    "company_name": asset["company_name"],
                    "sector": asset["sector"],
                    "price": round(current_price, 2),
                    "daily_change_pct": round(daily_change_pct, 2),
                    "volume": volume,
                    "sentiment_score": round(sentiment_score, 2),
                }
            )

    return market_rows


def save_market_data(market_rows: list[dict]) -> None:
    """Save fictional market history to a CSV file."""
    MARKET_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "date",
        "symbol",
        "company_name",
        "sector",
        "price",
        "daily_change_pct",
        "volume",
        "sentiment_score",
    ]

    with MARKET_DATA_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(market_rows)


def main() -> None:
    market_rows = generate_market_data()
    save_market_data(market_rows)

    print("Simulated market data created successfully.")
    print(f"File: {MARKET_DATA_PATH}")
    print(f"Assets: {len(ASSETS)}")
    print(f"Days per asset: {len(market_rows) // len(ASSETS)}")
    print(f"Total market records: {len(market_rows)}")


if __name__ == "__main__":
    main()
