import csv

from src.generate_market_data import (
    ASSETS,
    MARKET_DATA_PATH,
    generate_market_data,
)


REQUIRED_FIELDS = {
    "date",
    "symbol",
    "company_name",
    "sector",
    "price",
    "daily_change_pct",
    "volume",
    "sentiment_score",
}


def test_market_data_file_exists():
    assert MARKET_DATA_PATH.exists()


def test_generator_creates_expected_number_of_records():
    market_rows = generate_market_data(days=30, seed=42)

    assert len(market_rows) == 120


def test_generator_includes_all_four_assets():
    market_rows = generate_market_data(days=30, seed=42)
    generated_symbols = {row["symbol"] for row in market_rows}
    expected_symbols = {asset["symbol"] for asset in ASSETS}

    assert generated_symbols == expected_symbols


def test_each_market_record_has_required_fields():
    market_rows = generate_market_data(days=5, seed=42)

    for row in market_rows:
        assert set(row) == REQUIRED_FIELDS


def test_prices_and_volumes_are_positive():
    market_rows = generate_market_data(days=30, seed=42)

    for row in market_rows:
        assert row["price"] > 0
        assert row["volume"] > 0


def test_sentiment_scores_stay_within_valid_range():
    market_rows = generate_market_data(days=30, seed=42)

    for row in market_rows:
        assert -1.0 <= row["sentiment_score"] <= 1.0


def test_each_asset_has_thirty_records():
    market_rows = generate_market_data(days=30, seed=42)

    for asset in ASSETS:
        symbol = asset["symbol"]
        asset_rows = [
            row for row in market_rows
            if row["symbol"] == symbol
        ]

        assert len(asset_rows) == 30


def test_generation_is_reproducible():
    first_run = generate_market_data(days=10, seed=42)
    second_run = generate_market_data(days=10, seed=42)

    assert first_run == second_run


def test_saved_csv_contains_expected_rows():
    with MARKET_DATA_PATH.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        saved_rows = list(csv.DictReader(file))

    assert len(saved_rows) == 120
