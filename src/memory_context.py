import copy
from typing import Any


def build_memory_context(
    decision: dict[str, Any],
    memory: dict[str, Any],
) -> dict[str, Any]:
    """Build historical context for one decision."""
    symbol = decision["symbol"]
    asset_memory = memory.get(
        "assets",
        {},
    ).get(symbol)

    if asset_memory is None:
        return {
            "has_prior_memory": False,
            "times_previously_observed": 0,
            "previous_recommendation": None,
            "recommendation_consistent": None,
            "prior_price": None,
            "prior_risk_level": None,
            "memory_statement": (
                "No prior memory is available for "
                f"{symbol}."
            ),
        }

    previous_recommendation = asset_memory[
        "latest_recommendation"
    ]
    current_recommendation = decision[
        "proposed_action"
    ]
    recommendation_consistent = (
        previous_recommendation
        == current_recommendation
    )

    if recommendation_consistent:
        memory_statement = (
            f"The {current_recommendation} "
            "recommendation is consistent with "
            f"{asset_memory['times_observed']} "
            "previous observation(s)."
        )
    else:
        memory_statement = (
            "The recommendation changed from "
            f"{previous_recommendation} to "
            f"{current_recommendation}."
        )

    return {
        "has_prior_memory": True,
        "times_previously_observed": asset_memory[
            "times_observed"
        ],
        "previous_recommendation": (
            previous_recommendation
        ),
        "recommendation_consistent": (
            recommendation_consistent
        ),
        "prior_price": asset_memory["latest_price"],
        "prior_risk_level": asset_memory[
            "latest_risk_level"
        ],
        "memory_statement": memory_statement,
    }


def add_memory_context(
    decision_report: dict[str, Any],
    memory: dict[str, Any],
) -> dict[str, Any]:
    """Add historical context to every decision."""
    enriched_report = copy.deepcopy(
        decision_report
    )

    for decision in enriched_report["decisions"]:
        decision["memory_context"] = (
            build_memory_context(
                decision,
                memory,
            )
        )

    enriched_report["memory_cycles_available"] = (
        memory.get("total_cycles_remembered", 0)
    )

    return enriched_report
