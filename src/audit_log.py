import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_LOG_PATH = PROJECT_ROOT / "logs" / "audit_log.jsonl"
GENESIS_HASH = "GENESIS"


def read_audit_records(
    file_path: Path = AUDIT_LOG_PATH,
) -> list[dict[str, Any]]:
    """Read every JSON record from the audit log."""
    if not file_path.exists():
        return []

    records = []

    with file_path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    return records


def calculate_record_hash(
    record: dict[str, Any],
) -> str:
    """Calculate a stable SHA-256 hash for one record."""
    hashable_record = {
        key: value
        for key, value in record.items()
        if key != "record_hash"
    }

    serialized_record = json.dumps(
        hashable_record,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        serialized_record.encode("utf-8")
    ).hexdigest()


def create_audit_record(
    cycle: dict[str, Any],
    previous_hash: str,
) -> dict[str, Any]:
    """Create a compact audit record from an agent cycle."""
    governed_outcomes = []

    for item in cycle["governed_actions"]:
        decision = item["decision"]
        proposal = item["proposal"]
        gate_result = item["gate_result"]

        governed_outcomes.append(
            {
                "symbol": decision["symbol"],
                "recommendation": decision[
                    "proposed_action"
                ],
                "proposal_action": proposal[
                    "action_type"
                ],
                "governance_result": gate_result[
                    "governance_result"
                ],
                "executed": gate_result["executed"],
            }
        )

    record = {
        "schema_version": "1.0",
        "audit_id": str(uuid4()),
        "cycle_id": cycle["cycle_id"],
        "recorded_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "agent_name": cycle["agent_name"],
        "operating_mode": cycle["operating_mode"],
        "cycle_summary": cycle["cycle_summary"],
        "governed_outcomes": governed_outcomes,
        "previous_hash": previous_hash,
    }

    record["record_hash"] = calculate_record_hash(record)

    return record


def append_audit_record(
    cycle: dict[str, Any],
    file_path: Path = AUDIT_LOG_PATH,
) -> dict[str, Any]:
    """Append one cycle to the hash-chained audit log."""
    existing_records = read_audit_records(file_path)

    if existing_records:
        previous_hash = existing_records[-1][
            "record_hash"
        ]
    else:
        previous_hash = GENESIS_HASH

    record = create_audit_record(
        cycle,
        previous_hash,
    )

    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("a", encoding="utf-8") as file:
        file.write(
            json.dumps(record, sort_keys=True) + "\n"
        )

    return record


def verify_audit_chain(
    file_path: Path = AUDIT_LOG_PATH,
) -> bool:
    """Verify every record and hash link in the log."""
    records = read_audit_records(file_path)
    expected_previous_hash = GENESIS_HASH

    for record in records:
        if record["previous_hash"] != (
            expected_previous_hash
        ):
            return False

        expected_record_hash = calculate_record_hash(
            record
        )

        if record["record_hash"] != (
            expected_record_hash
        ):
            return False

        expected_previous_hash = record["record_hash"]

    return True
