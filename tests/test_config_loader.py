import json

import pytest

from src.config_loader import (
    load_agent_config,
    load_identity,
    load_json_file,
    load_policy,
)


def test_load_policy_returns_governing_policy():
    policy = load_policy()

    assert policy["policy_name"] == (
        "Governed Autonomous Market Agent Policy"
    )
    assert policy["operating_mode"] == "autonomous_sandbox"


def test_load_identity_returns_aureus_identity():
    identity = load_identity()

    assert identity["agent_name"] == "Aureus"
    assert identity["identity_version"] == "1.0"


def test_load_agent_config_combines_identity_and_policy():
    config = load_agent_config()

    assert "identity" in config
    assert "policy" in config
    assert config["identity"]["agent_name"] == "Aureus"
    assert config["policy"]["operating_mode"] == "autonomous_sandbox"


def test_missing_json_file_raises_error(tmp_path):
    missing_file = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        load_json_file(missing_file)


def test_invalid_json_file_raises_error(tmp_path):
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text(
        '{"agent_name": "Aureus"',
        encoding="utf-8",
    )

    with pytest.raises(json.JSONDecodeError):
        load_json_file(invalid_file)
