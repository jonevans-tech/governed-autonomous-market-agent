import copy

from src.agent_cycle import run_agent_cycle
from src.memory import (
    MAX_RECENT_CYCLES,
    create_empty_memory,
    load_memory,
    save_memory,
    update_memory,
)


def test_empty_memory_starts_with_zero_cycles():
    memory = create_empty_memory("Aureus")

    assert memory["agent_name"] == "Aureus"
    assert memory["total_cycles_remembered"] == 0
    assert memory["assets"] == {}
    assert memory["processed_cycle_ids"] == []


def test_missing_memory_file_returns_empty_memory(
    tmp_path,
):
    memory_path = tmp_path / "missing_memory.json"

    memory = load_memory(
        memory_path,
        agent_name="Aureus",
    )

    assert memory["total_cycles_remembered"] == 0
    assert memory["agent_name"] == "Aureus"


def test_first_cycle_updates_memory():
    memory = create_empty_memory("Aureus")
    cycle = run_agent_cycle()

    updated_memory = update_memory(memory, cycle)

    assert updated_memory[
        "total_cycles_remembered"
    ] == 1
    assert len(updated_memory["assets"]) == 4
    assert updated_memory["assets"]["AUR"][
        "times_observed"
    ] == 1
    assert updated_memory["last_cycle_id"] == (
        cycle["cycle_id"]
    )


def test_duplicate_cycle_is_ignored():
    memory = create_empty_memory("Aureus")
    cycle = run_agent_cycle()

    memory = update_memory(memory, cycle)
    duplicate_result = update_memory(memory, cycle)

    assert duplicate_result[
        "total_cycles_remembered"
    ] == 1
    assert duplicate_result["assets"]["AUR"][
        "times_observed"
    ] == 1
    assert len(
        duplicate_result["processed_cycle_ids"]
    ) == 1


def test_second_unique_cycle_is_remembered():
    memory = create_empty_memory("Aureus")
    first_cycle = run_agent_cycle()
    second_cycle = run_agent_cycle()

    memory = update_memory(memory, first_cycle)
    memory = update_memory(memory, second_cycle)

    assert memory["total_cycles_remembered"] == 2
    assert memory["assets"]["AUR"][
        "times_observed"
    ] == 2
    assert len(memory["processed_cycle_ids"]) == 2


def test_recommendation_change_is_remembered():
    memory = create_empty_memory("Aureus")
    first_cycle = run_agent_cycle()
    second_cycle = copy.deepcopy(
        run_agent_cycle()
    )

    second_cycle["governed_actions"][0][
        "decision"
    ]["proposed_action"] = "HOLD"

    memory = update_memory(memory, first_cycle)
    memory = update_memory(memory, second_cycle)

    aurora_memory = memory["assets"]["AUR"]

    assert aurora_memory[
        "previous_recommendation"
    ] == "AVOID"
    assert aurora_memory[
        "latest_recommendation"
    ] == "HOLD"
    assert aurora_memory[
        "recommendation_changed"
    ] is True
    assert aurora_memory[
        "recommendation_changes"
    ] == 1


def test_price_change_is_calculated():
    memory = create_empty_memory("Aureus")
    first_cycle = run_agent_cycle()
    second_cycle = copy.deepcopy(
        run_agent_cycle()
    )

    for observation in second_cycle[
        "observation"
    ]["assets"]:
        if observation["symbol"] == "AUR":
            observation["latest_price"] += 5.00

    memory = update_memory(memory, first_cycle)
    memory = update_memory(memory, second_cycle)

    assert memory["assets"]["AUR"][
        "price_change_since_last_cycle"
    ] == 5.00


def test_recent_cycle_history_is_limited():
    memory = create_empty_memory("Aureus")
    base_cycle = run_agent_cycle()

    for cycle_number in range(25):
        cycle = copy.deepcopy(base_cycle)
        cycle["cycle_id"] = f"cycle-{cycle_number}"
        memory = update_memory(memory, cycle)

    assert memory["total_cycles_remembered"] == 25
    assert len(memory["recent_cycles"]) == (
        MAX_RECENT_CYCLES
    )
    assert memory["recent_cycles"][0][
        "cycle_id"
    ] == "cycle-5"
    assert memory["recent_cycles"][-1][
        "cycle_id"
    ] == "cycle-24"


def test_memory_can_be_saved_and_loaded(tmp_path):
    memory_path = tmp_path / "memory.json"
    memory = create_empty_memory("Aureus")
    memory = update_memory(
        memory,
        run_agent_cycle(),
    )

    save_memory(memory, memory_path)
    loaded_memory = load_memory(memory_path)

    assert loaded_memory == memory
