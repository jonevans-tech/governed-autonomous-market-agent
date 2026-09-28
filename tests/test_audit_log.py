import json

from src.agent_cycle import run_agent_cycle
from src.audit_log import (
    GENESIS_HASH,
    append_audit_record,
    calculate_record_hash,
    create_audit_record,
    read_audit_records,
    verify_audit_chain,
)


def test_missing_audit_log_returns_empty_list(
    tmp_path,
):
    audit_path = tmp_path / "missing.jsonl"

    records = read_audit_records(audit_path)

    assert records == []


def test_created_record_has_valid_hash():
    cycle = run_agent_cycle()

    record = create_audit_record(
        cycle,
        GENESIS_HASH,
    )

    assert record["previous_hash"] == GENESIS_HASH
    assert record["record_hash"] == (
        calculate_record_hash(record)
    )
    assert record["cycle_id"] == cycle["cycle_id"]


def test_first_appended_record_uses_genesis_hash(
    tmp_path,
):
    audit_path = tmp_path / "audit.jsonl"
    cycle = run_agent_cycle()

    record = append_audit_record(
        cycle,
        audit_path,
    )

    assert record["previous_hash"] == GENESIS_HASH
    assert len(read_audit_records(audit_path)) == 1


def test_second_record_links_to_first_record(
    tmp_path,
):
    audit_path = tmp_path / "audit.jsonl"

    first_record = append_audit_record(
        run_agent_cycle(),
        audit_path,
    )
    second_record = append_audit_record(
        run_agent_cycle(),
        audit_path,
    )

    assert second_record["previous_hash"] == (
        first_record["record_hash"]
    )


def test_valid_audit_chain_passes_verification(
    tmp_path,
):
    audit_path = tmp_path / "audit.jsonl"

    append_audit_record(
        run_agent_cycle(),
        audit_path,
    )
    append_audit_record(
        run_agent_cycle(),
        audit_path,
    )

    assert verify_audit_chain(audit_path) is True


def test_modified_record_breaks_verification(
    tmp_path,
):
    audit_path = tmp_path / "audit.jsonl"

    append_audit_record(
        run_agent_cycle(),
        audit_path,
    )

    records = read_audit_records(audit_path)
    records[0]["cycle_summary"]["allowed"] = 999

    audit_path.write_text(
        json.dumps(records[0]) + "\n",
        encoding="utf-8",
    )

    assert verify_audit_chain(audit_path) is False


def test_removed_record_breaks_verification(
    tmp_path,
):
    audit_path = tmp_path / "audit.jsonl"

    append_audit_record(
        run_agent_cycle(),
        audit_path,
    )
    append_audit_record(
        run_agent_cycle(),
        audit_path,
    )

    records = read_audit_records(audit_path)

    audit_path.write_text(
        json.dumps(records[1]) + "\n",
        encoding="utf-8",
    )

    assert verify_audit_chain(audit_path) is False
