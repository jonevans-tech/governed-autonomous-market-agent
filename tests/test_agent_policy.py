import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = PROJECT_ROOT / "config" / "agent_policy.json"


def load_policy():
    with POLICY_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def test_policy_file_exists():
    assert POLICY_PATH.exists()


def test_agent_uses_autonomous_sandbox():
    policy = load_policy()

    assert policy["operating_mode"] == "autonomous_sandbox"


def test_real_financial_activity_is_prohibited():
    policy = load_policy()
    prohibited = policy["prohibited_actions"]

    assert "use_real_money" in prohibited
    assert "execute_real_financial_transaction" in prohibited
    assert "access_cryptocurrency_wallet" in prohibited


def test_external_publication_requires_approval():
    policy = load_policy()

    assert (
        "publish_external_content"
        in policy["approval_required_actions"]
    )


def test_virtual_trade_limit_is_five_thousand():
    policy = load_policy()

    assert policy["financial_limits"]["maximum_trade_value"] == 5000.0


def test_every_decision_requires_audit_and_explanation():
    policy = load_policy()
    limits = policy["operational_limits"]

    assert limits["audit_every_decision"] is True
    assert limits["require_explanation"] is True


def test_allowed_and_prohibited_actions_do_not_overlap():
    policy = load_policy()

    allowed = set(policy["allowed_actions"])
    prohibited = set(policy["prohibited_actions"])

    assert allowed.isdisjoint(prohibited)
