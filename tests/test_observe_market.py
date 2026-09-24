import json

from src.observe_market import (
    classify_sentiment,
    classify_trend,
    classify_volatility,
    create_market_observation,
    load_market_history,
    save_market_observation,
)


def test_load_market_history_returns_120_rows():
    market_rows = load_market_history()

    assert len(market_rows) == 120


def test_market_numeric_fields_are_converted():
    first_row = load_market_history()[0]

    assert isinstance(first_row["price"], float)
    assert isinstance(first_row["daily_change_pct"], float)
    assert isinstance(first_row["volume"], int)
    assert isinstance(first_row["sentiment_score"], float)


def test_observation_contains_four_assets():
    observation = create_market_observation(
        load_market_history()
    )

    assert observation["asset_count"] == 4
    assert len(observation["assets"]) == 4


def test_observation_symbols_are_sorted():
    observation = create_market_observation(
        load_market_history()
    )
    symbols = [
        asset["symbol"] for asset in observation["assets"]
    ]

    assert symbols == ["AUR", "GRD", "HBR", "MED"]


def test_aurora_is_downward_and_high_risk():
    observation = create_market_observation(
        load_market_history()
    )
    aurora = observation["assets"][0]

    assert aurora["symbol"] == "AUR"
    assert aurora["trend"] == "downward"
    assert aurora["risk_level"] == "high"
    assert aurora["total_return_pct"] == -6.12


def test_trend_classification_boundaries():
    assert classify_trend(3.0) == "upward"
    assert classify_trend(-3.0) == "downward"
    assert classify_trend(1.0) == "sideways"


def test_sentiment_classification_boundaries():
    assert classify_sentiment(0.25) == "positive"
    assert classify_sentiment(-0.25) == "negative"
    assert classify_sentiment(0.0) == "mixed"


def test_volatility_classification_boundaries():
    assert classify_volatility(1.75) == "high"
    assert classify_volatility(1.00) == "moderate"
    assert classify_volatility(0.50) == "low"


def test_observation_can_be_saved_as_json(tmp_path):
    observation = create_market_observation(
        load_market_history()
    )
    output_path = tmp_path / "observation.json"

    save_market_observation(observation, output_path)

    saved_observation = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert saved_observation == observation
