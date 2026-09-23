import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"

POLICY_PATH = CONFIG_DIR / "agent_policy.json"
IDENTITY_PATH = CONFIG_DIR / "agent_identity.json"


def load_json_file(file_path: Path) -> dict[str, Any]:
    """Load and return a JSON configuration file."""
    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_policy() -> dict[str, Any]:
    """Load the agent's governing policy."""
    return load_json_file(POLICY_PATH)


def load_identity() -> dict[str, Any]:
    """Load the agent's identity and goals."""
    return load_json_file(IDENTITY_PATH)


def load_agent_config() -> dict[str, dict[str, Any]]:
    """Load all configuration required by the agent."""
    return {
        "identity": load_identity(),
        "policy": load_policy(),
    }


def print_config_summary() -> None:
    """Display a short summary without printing the entire configuration."""
    config = load_agent_config()
    identity = config["identity"]
    policy = config["policy"]

    print("Agent configuration loaded successfully.")
    print(f"Agent: {identity['agent_name']}")
    print(f"Purpose: {identity['purpose']}")
    print(f"Operating mode: {policy['operating_mode']}")
    print(
        "Starting virtual cash: "
        f"${policy['financial_limits']['starting_virtual_cash']:,.2f}"
    )
    print(
        "Maximum virtual trade: "
        f"${policy['financial_limits']['maximum_trade_value']:,.2f}"
    )


if __name__ == "__main__":
    print_config_summary()
