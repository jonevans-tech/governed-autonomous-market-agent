import json
from pathlib import Path
from typing import Any

from src.config_loader import load_agent_config
from src.observe_market import (
    create_market_observation,
    load_market_history,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DECISION_PATH = (
    PROJECT_ROOT
    / "data"
    / "state"
    / "latest_decisions.json"
)


def calculate_decision_score(
    asset: dict[str, Any],
) -> tuple[int, list[str]]:
    """Score one asset and record the evidence used."""
    score = 0
    reasons = []

    if asset["trend"] == "upward":
        score += 2
        reasons.append("Price trend is upward.")
    elif asset["trend"] == "downward":
        score -= 2
        reasons.append("Price trend is downward.")
    else:
        reasons.append("Price trend is sideways.")

    if asset["sentiment"] == "positive":
        score += 1
        reasons.append("Average sentiment is positive.")
    elif asset["sentiment"] == "negative":
        score -= 1
        reasons.append("Average sentiment is negative.")
    else:
        reasons.append("Average sentiment is mixed.")

    if asset["risk_level"] == "high":
        score -= 2
        reasons.append("Observed volatility is high.")
    elif asset["risk_level"] == "moderate":
        score -= 1
        reasons.append("Observed volatility is moderate.")
    else:
        reasons.append("Observed volatility is low.")

    return score, reasons


def determine_action(
    asset: dict[str, Any],
    score: int,
) -> tuple[str, str]:
    """Choose a proposed action from the score and safeguards."""
    if (
        asset["trend"] == "downward"
        and asset["risk_level"] == "high"
    ):
        return (
            "AVOID",
            "Downward performance combined with high volatility.",
        )

    if asset["total_return_pct"] > 15.0:
        return (
            "WATCH",
            "Strong recent gains may indicate overextension.",
        )

    if score >= 2:
        return (
            "BUY",
            "Positive evidence outweighs the observed risks.",
        )

    if score >= 0:
        return (
            "HOLD",
            "Evidence is not strong enough to justify a new position.",
        )

    return (
        "WATCH",
        "Risk currently outweighs the positive evidence.",
    )


def classify_confidence(score: int) -> str:
    """Describe how strongly the evidence supports the result."""
    absolute_score = abs(score)

    if absolute_score >= 3:
        return "high"
    if absolute_score >= 2:
        return "moderate"
    return "low"


def evaluate_asset(
    asset: dict[str, Any],
) -> dict[str, Any]:
    """Create a governed recommendation for one asset."""
    score, reasons = calculate_decision_score(asset)
    proposed_action, decision_summary = determine_action(
        asset,
        score,
    )

    return {
        "symbol": asset["symbol"],
        "company_name": asset["company_name"],
        "proposed_action": proposed_action,
        "decision_score": score,
        "confidence": classify_confidence(score),
        "decision_summary": decision_summary,
        "evidence": reasons,
        "uncertainty": (
            "The decision uses simulated historical data and "
            "cannot predict future performance."
        ),
        "requires_approval": proposed_action == "BUY",
        "trade_executed": False,
    }


def create_decision_report(
    observation: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate every observed asset."""
    config = load_agent_config()
    identity = config["identity"]
    policy = config["policy"]

    decisions = [
        evaluate_asset(asset)
        for asset in observation["assets"]
    ]

    return {
        "agent_name": identity["agent_name"],
        "operating_mode": policy["operating_mode"],
        "decision_type": "recommendation_only",
        "observation_type": observation["observation_type"],
        "decisions": decisions,
    }


def save_decision_report(
    report: dict[str, Any],
    file_path: Path = DECISION_PATH,
) -> None:
    """Save the latest recommendations as runtime state."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)


def print_decision_report(
    report: dict[str, Any],
) -> None:
    """Display Aureus's proposed actions."""
    print("Aureus decision report")
    print("======================")

    for decision in report["decisions"]:
        approval_text = (
            "approval required"
            if decision["requires_approval"]
            else "no approval needed"
        )

        print(
            f"{decision['symbol']} | "
            f"{decision['proposed_action']} | "
            f"Score: {decision['decision_score']:+d} | "
            f"Confidence: {decision['confidence']} | "
            f"{approval_text}"
        )
        print(f"  Reason: {decision['decision_summary']}")


def main() -> None:
    market_rows = load_market_history()
    observation = create_market_observation(market_rows)
    report = create_decision_report(observation)

    save_decision_report(report)
    print_decision_report(report)

    print()
    print("No trades were executed.")
    print(f"Decision report saved to: {DECISION_PATH}")


if __name__ == "__main__":
    main()
