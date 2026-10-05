import copy

from src.agent_cycle import run_agent_cycle
from src.memory import (
    create_empty_memory,
    update_memory,
)
from src.memory_context import (
    add_memory_context,
    build_memory_context,
)


def test_no_prior_memory_is_reported():
    memory = create_empty_memory("Aureus")
    decision = {
        "symbol": "AUR",
        "proposed_action": "AVOID",
    }

    context = build_memory_context(
        decision,
        memory,
    )

    assert context["has_prior_memory"] is False
    assert context["previous_recommendation"] is None
    assert "No prior memory" in (
        context["memory_statement"]
    )


def test_consistent_recommendation_is_recognized():
    memory = create_empty_memory("Aureus")
    first_cycle = run_agent_cycle()
    memory = update_memory(memory, first_cycle)

    decision = {
        "symbol": "AUR",
        "proposed_action": "AVOID",
    }

    context = build_memory_context(
        decision,
        memory,
    )

    assert context["has_prior_memory"] is True
    assert context[
        "recommendation_consistent"
    ] is True
    assert context[
        "times_previously_observed"
    ] == 1
    assert "consistent" in context[
        "memory_statement"
    ]


def test_changed_recommendation_is_recognized():
    memory = create_empty_memory("Aureus")
    first_cycle = run_agent_cycle()
    memory = update_memory(memory, first_cycle)

    decision = {
        "symbol": "AUR",
        "proposed_action": "HOLD",
    }

    context = build_memory_context(
        decision,
        memory,
    )

    assert context[
        "recommendation_consistent"
    ] is False
    assert context[
        "previous_recommendation"
    ] == "AVOID"
    assert "changed from AVOID to HOLD" in (
        context["memory_statement"]
    )


def test_every_decision_receives_memory_context():
    memory = create_empty_memory("Aureus")
    cycle = run_agent_cycle()
    report = cycle["decision_report"]

    enriched_report = add_memory_context(
        report,
        memory,
    )

    for decision in enriched_report["decisions"]:
        assert "memory_context" in decision


def test_enrichment_does_not_modify_original_report():
    memory = create_empty_memory("Aureus")
    cycle = run_agent_cycle()
    original_report = copy.deepcopy(
        cycle["decision_report"]
    )

    add_memory_context(
        cycle["decision_report"],
        memory,
    )

    assert cycle["decision_report"] == original_report


def test_cycle_uses_supplied_memory():
    memory = create_empty_memory("Aureus")
    first_cycle = run_agent_cycle()
    memory = update_memory(memory, first_cycle)

    second_cycle = run_agent_cycle(memory)
    first_decision = second_cycle[
        "decision_report"
    ]["decisions"][0]
    context = first_decision["memory_context"]

    assert context["has_prior_memory"] is True
    assert context[
        "times_previously_observed"
    ] == 1


def test_cycle_without_supplied_memory_starts_empty():
    cycle = run_agent_cycle()
    first_decision = cycle[
        "decision_report"
    ]["decisions"][0]

    assert first_decision["memory_context"][
        "has_prior_memory"
    ] is False
    assert cycle["decision_report"][
        "memory_cycles_available"
    ] == 0