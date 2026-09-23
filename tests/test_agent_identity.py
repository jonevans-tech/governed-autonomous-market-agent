import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IDENTITY_PATH = PROJECT_ROOT / "config" / "agent_identity.json"


def load_identity():
    with IDENTITY_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def test_identity_file_exists():
    assert IDENTITY_PATH.exists()


def test_agent_name_is_aureus():
    identity = load_identity()

    assert identity["agent_name"] == "Aureus"


def test_agent_has_defined_goals():
    identity = load_identity()

    assert identity["primary_goal"]
    assert len(identity["secondary_goals"]) >= 3


def test_agent_cannot_claim_to_be_human_or_conscious():
    identity = load_identity()
    boundaries = identity["identity_boundaries"]

    assert boundaries["may_claim_to_be_conscious"] is False
    assert boundaries["may_claim_to_be_human"] is False
    assert boundaries["may_hide_ai_identity"] is False


def test_agent_cannot_rewrite_identity_or_goals():
    identity = load_identity()
    boundaries = identity["identity_boundaries"]

    assert boundaries["may_modify_own_identity"] is False
    assert boundaries["may_modify_own_goals"] is False


def test_agent_must_explain_reasoning_and_uncertainty():
    identity = load_identity()
    style = identity["communication_style"]

    assert style["explains_reasoning"] is True
    assert style["admits_uncertainty"] is True
    assert style["distinguishes_facts_from_opinions"] is True


def test_self_description_discloses_simulation_and_oversight():
    identity = load_identity()
    description = identity["self_description"].lower()

    assert "simulated" in description
    assert "human oversight" in description
