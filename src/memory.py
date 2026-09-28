import copy
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEMORY_PATH = (
    PROJECT_ROOT
    / "data"
    / "state"
    / "agent_memory.json"
)
LATEST_CYCLE_PATH = (
    PROJECT_ROOT
    / "data"
    / "state"
    / "latest_agent_cycle.json"
)

MAX_RECENT_CYCLES = 20
MAX_PROCESSED_CYCLE_IDS = 100


def create_empty_memory(
    agent_name: str,
) -> dict[str, Any]:
    """Create a new persistent-memory structure."""
    return {
        "schema_version": "1.0",
        "agent_name": agent_name,
        "total_cycles_remembered": 0,
        "first_cycle_at": None,
        "last_cycle_at": None,
        "last_cycle_id": None,
        "assets": {},
        "recent_cycles": [],
        "processed_cycle_ids": [],
    }


def load_memory(
    file_path: Path = MEMORY_PATH,
    agent_name: str = "Aureus",
) -> dict[str, Any]:
    """Load existing memory or create empty memory."""
    if not file_path.exists():
        return create_empty_memory(agent_name)

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def find_asset_observation(
    cycle: dict[str, Any],
    symbol: str,
) -> dict[str, Any]:
    """Find one asset in the cycle observation."""
    for asset in cycle["observation"]["assets"]:
        if asset["symbol"] == symbol:
            return asset

    raise ValueError(
        f"Observation not found for symbol: {symbol}"
    )


def update_asset_memory(
    existing_memory: dict[str, Any] | None,
    decision: dict[str, Any],
    observation: dict[str, Any],
    cycle: dict[str, Any],
) -> dict[str, Any]:
    """Update persistent memory for one asset."""
    current_recommendation = decision[
        "proposed_action"
    ]

    if existing_memory is None:
        previous_recommendation = None
        recommendation_changes = 0
        times_observed = 0
        prior_price = None
    else:
        previous_recommendation = existing_memory[
            "latest_recommendation"
        ]
        recommendation_changes = existing_memory[
            "recommendation_changes"
        ]
        times_observed = existing_memory[
            "times_observed"
        ]
        prior_price = existing_memory["latest_price"]

    recommendation_changed = (
        previous_recommendation is not None
        and previous_recommendation
        != current_recommendation
    )

    if recommendation_changed:
        recommendation_changes += 1

    if prior_price is None:
        price_change_since_last_cycle = None
    else:
        price_change_since_last_cycle = round(
            observation["latest_price"] - prior_price,
            2,
        )

    return {
        "symbol": decision["symbol"],
        "company_name": decision["company_name"],
        "times_observed": times_observed + 1,
        "first_observed_at": (
            existing_memory["first_observed_at"]
            if existing_memory
            else cycle["completed_at"]
        ),
        "last_observed_at": cycle["completed_at"],
        "previous_recommendation": (
            previous_recommendation
        ),
        "latest_recommendation": (
            current_recommendation
        ),
        "recommendation_changed": (
            recommendation_changed
        ),
        "recommendation_changes": (
            recommendation_changes
        ),
        "prior_price": prior_price,
        "latest_price": observation["latest_price"],
        "price_change_since_last_cycle": (
            price_change_since_last_cycle
        ),
        "latest_trend": observation["trend"],
        "latest_sentiment": observation["sentiment"],
        "latest_risk_level": observation["risk_level"],
    }


def update_memory(
    memory: dict[str, Any],
    cycle: dict[str, Any],
) -> dict[str, Any]:
    """Update working memory from one completed cycle."""
    updated_memory = copy.deepcopy(memory)
    processed_cycle_ids = updated_memory.setdefault(
        "processed_cycle_ids",
        [
            recent_cycle["cycle_id"]
            for recent_cycle in updated_memory.get(
                "recent_cycles",
                [],
            )
        ],
    )

    if cycle["cycle_id"] in processed_cycle_ids:
        return updated_memory
    if updated_memory["first_cycle_at"] is None:
        updated_memory["first_cycle_at"] = cycle[
            "completed_at"
        ]

    for item in cycle["governed_actions"]:
        decision = item["decision"]
        symbol = decision["symbol"]
        observation = find_asset_observation(
            cycle,
            symbol,
        )
        existing_asset_memory = updated_memory[
            "assets"
        ].get(symbol)

        updated_memory["assets"][symbol] = (
            update_asset_memory(
                existing_asset_memory,
                decision,
                observation,
                cycle,
            )
        )

    recommendations = {
        item["decision"]["symbol"]: item[
            "decision"
        ]["proposed_action"]
        for item in cycle["governed_actions"]
    }

    updated_memory["recent_cycles"].append(
        {
            "cycle_id": cycle["cycle_id"],
            "completed_at": cycle["completed_at"],
            "recommendations": recommendations,
            "cycle_summary": cycle["cycle_summary"],
        }
    )

    updated_memory["recent_cycles"] = (
        updated_memory["recent_cycles"][
            -MAX_RECENT_CYCLES:
        ]
    )

    updated_memory["total_cycles_remembered"] += 1
    updated_memory["last_cycle_at"] = cycle[
        "completed_at"
    ]
    updated_memory["last_cycle_id"] = cycle[
    "cycle_id"
]

    updated_memory["processed_cycle_ids"].append(
    cycle["cycle_id"]
)
    updated_memory["processed_cycle_ids"] = (
    updated_memory["processed_cycle_ids"][
        -MAX_PROCESSED_CYCLE_IDS:
    ]
)

    return updated_memory  


def save_memory(
    memory: dict[str, Any],
    file_path: Path = MEMORY_PATH,
) -> None:
    """Save working memory as JSON."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(memory, file, indent=2)


def print_memory_summary(
    memory: dict[str, Any],
) -> None:
    """Display the important parts of memory."""
    print("Aureus persistent memory")
    print("========================")
    print(
        "Cycles remembered: "
        f"{memory['total_cycles_remembered']}"
    )

    for symbol in sorted(memory["assets"]):
        asset = memory["assets"][symbol]

        print(
            f"{symbol} | "
            f"Observed: {asset['times_observed']} | "
            f"Previous: "
            f"{asset['previous_recommendation']} | "
            f"Current: "
            f"{asset['latest_recommendation']} | "
            f"Changed: "
            f"{asset['recommendation_changed']}"
        )


def main() -> None:
    with LATEST_CYCLE_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        cycle = json.load(file)

    memory = load_memory(
        agent_name=cycle["agent_name"]
    )
    updated_memory = update_memory(memory, cycle)
    save_memory(updated_memory)
    print_memory_summary(updated_memory)


if __name__ == "__main__":
    main()
