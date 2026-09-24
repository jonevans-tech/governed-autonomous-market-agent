import json

from src.decision_engine import (
    calculate_decision_score,
    classify_confidence,
    create_decision_report,
    determine_action,
    evaluate_asset,
    save_decision_report,
)
from src.observe_market import (
    create_market_observation,
    load_market_history,
)


def make_test_asset(**overrides):
    asset = {
        "symbol": "TST",
        "company_name": "Test Company",
        "sector": "Testing",
        "total_return_pct": 8.0,
        "trend": "upward",
        "sentiment": "positive",
        "risk_level": "low",
    }
    asset.update(overrides)
    return asset


def test_positive_low_risk_asset_receives_score_three():
    asset = make_test_asset()

    score, reasons = calculate_decision_score(asset)

    assert score == 3
    assert "Price trend is upward." in reasons
    assert "Average sentiment is positive." in reasons
    assert "Observed volatility is low." in reasons


def test_downward_high_risk_asset_is_avoided():
    asset = make_test_asset(
        trend="downward",
        sentiment="mixed",
        risk_level="high",
        total_return_pct=-6.0,
    )
    score, _ = calculate_decision_score(asset)
    action, summary = determine_action(asset, score)

    assert action == "AVOID"
    assert "high volatility" in summary


def test_overextended_asset_is_watched():
    asset = make_test_asset(total_return_pct=20.0)
    score, _ = calculate_decision_score(asset)
    action, summary = determine_action(asset, score)

    assert action == "WATCH"
    assert "overextension" in summary


def test_positive_low_risk_asset_produces_buy():
    asset = make_test_asset()
    score, _ = calculate_decision_score(asset)
    action, _ = determine_action(asset, score)

    assert action == "BUY"


def test_buy_recommendation_requires_approval():
    decision = evaluate_asset(make_test_asset())

    assert decision["proposed_action"] == "BUY"
    assert decision["requires_approval"] is True
    assert decision["trade_executed"] is False


def test_confidence_is_based_on_score_strength():
    assert classify_confidence(4) == "high"
    assert classify_confidence(-3) == "high"
    assert classify_confidence(2) == "moderate"
    assert classify_confidence(1) == "low"


def test_decision_report_has_governance_metadata():
    observation = create_market_observation(
        load_market_history()
    )
    report = create_decision_report(observation)

    assert report["agent_name"] == "Aureus"
    assert report["operating_mode"] == "autonomous_sandbox"
    assert report["decision_type"] == "recommendation_only"
    assert len(report["decisions"]) == 4


def test_current_report_executes_no_trades():
    observation = create_market_observation(
        load_market_history()
    )
    report = create_decision_report(observation)

    for decision in report["decisions"]:
        assert decision["trade_executed"] is False


def test_decision_report_can_be_saved(tmp_path):
    observation = create_market_observation(
        load_market_history()
    )
    report = create_decision_report(observation)
    output_path = tmp_path / "decisions.json"

    save_decision_report(report, output_path)

    saved_report = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert saved_report == report
