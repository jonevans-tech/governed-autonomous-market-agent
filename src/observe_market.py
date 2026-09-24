import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MARKET_DATA_PATH = PROJECT_ROOT / "data" / "market" / "market_history.csv"
OBSERVATION_PATH = (
    PROJECT_ROOT
    / "data"
    / "state"
    / "latest_market_observation.json"
)


def load_market_history(
    file_path: Path = MARKET_DATA_PATH,
) -> list[dict[str, Any]]:
    """Load market history and convert numeric fields."""
    market_rows = []

    with file_path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            market_rows.append(
                {
                    "date": row["date"],
                    "symbol": row["symbol"],
                    "company_name": row["company_name"],
                    "sector": row["sector"],
                    "price": float(row["price"]),
                    "daily_change_pct": float(
                        row["daily_change_pct"]
                    ),
                    "volume": int(row["volume"]),
                    "sentiment_score": float(
                        row["sentiment_score"]
                    ),
                }
            )

    return market_rows


def classify_trend(total_return_pct: float) -> str:
    """Classify price movement over the observation period."""
    if total_return_pct > 2.0:
        return "upward"
    if total_return_pct < -2.0:
        return "downward"
    return "sideways"


def classify_sentiment(average_sentiment: float) -> str:
    """Classify average market sentiment."""
    if average_sentiment > 0.15:
        return "positive"
    if average_sentiment < -0.15:
        return "negative"
    return "mixed"


def classify_volatility(volatility: float) -> str:
    """Classify daily price volatility."""
    if volatility > 1.50:
        return "high"
    if volatility > 0.80:
        return "moderate"
    return "low"


def analyze_asset(
    asset_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize one asset's market history."""
    first_row = asset_rows[0]
    latest_row = asset_rows[-1]

    first_price = first_row["price"]
    latest_price = latest_row["price"]

    total_return_pct = (
        (latest_price - first_price) / first_price
    ) * 100

    daily_changes = [
        row["daily_change_pct"] for row in asset_rows
    ]
    sentiment_scores = [
        row["sentiment_score"] for row in asset_rows
    ]
    volumes = [row["volume"] for row in asset_rows]

    volatility = pstdev(daily_changes)
    average_sentiment = mean(sentiment_scores)

    return {
        "symbol": latest_row["symbol"],
        "company_name": latest_row["company_name"],
        "sector": latest_row["sector"],
        "observation_start": first_row["date"],
        "observation_end": latest_row["date"],
        "first_price": round(first_price, 2),
        "latest_price": round(latest_price, 2),
        "total_return_pct": round(total_return_pct, 2),
        "average_daily_change_pct": round(
            mean(daily_changes),
            2,
        ),
        "average_volume": round(mean(volumes)),
        "average_sentiment": round(average_sentiment, 2),
        "volatility": round(volatility, 2),
        "trend": classify_trend(total_return_pct),
        "sentiment": classify_sentiment(average_sentiment),
        "risk_level": classify_volatility(volatility),
    }


def create_market_observation(
    market_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create a summarized observation for every asset."""
    rows_by_symbol = defaultdict(list)

    for row in market_rows:
        rows_by_symbol[row["symbol"]].append(row)

    asset_observations = []

    for symbol in sorted(rows_by_symbol):
        asset_observations.append(
            analyze_asset(rows_by_symbol[symbol])
        )

    return {
        "observation_type": "simulated_market_summary",
        "asset_count": len(asset_observations),
        "assets": asset_observations,
    }


def save_market_observation(
    observation: dict[str, Any],
    file_path: Path = OBSERVATION_PATH,
) -> None:
    """Save the latest market observation as agent state."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(observation, file, indent=2)


def print_market_observation(
    observation: dict[str, Any],
) -> None:
    """Display a readable summary of the observation."""
    print("Aureus market observation")
    print("==========================")

    for asset in observation["assets"]:
        print(
            f"{asset['symbol']} | "
            f"${asset['latest_price']:,.2f} | "
            f"Return: {asset['total_return_pct']:+.2f}% | "
            f"Trend: {asset['trend']} | "
            f"Sentiment: {asset['sentiment']} | "
            f"Risk: {asset['risk_level']}"
        )


def main() -> None:
    market_rows = load_market_history()
    observation = create_market_observation(market_rows)
    save_market_observation(observation)
    print_market_observation(observation)

    print()
    print(f"Observation saved to: {OBSERVATION_PATH}")


if __name__ == "__main__":
    main()
