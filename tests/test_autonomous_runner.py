"""Tests for the governed autonomous runner."""

import json

import pytest

from src.autonomous_runner import (
    build_argument_parser,
    create_runner_status,
    run_autonomous_runner,
    validate_runner_settings,
)


def test_runner_status_starts_with_safe_defaults():
    """New runner state must explicitly disable real money."""

    status = create_runner_status(
        interval_seconds=60,
        maximum_cycles=1,
    )

    assert status["status"] == "STARTING"
    assert status["cycles_completed"] == 0
    assert status["failures"] == 0
    assert status["uses_real_money"] is False


def test_interval_below_policy_minimum_is_rejected():
    """The runner cannot bypass the policy interval."""

    with pytest.raises(
        ValueError,
        match="below the policy minimum",
    ):
        validate_runner_settings(
            interval_seconds=30,
            minimum_interval_seconds=60,
            maximum_cycles=1,
        )


@pytest.mark.parametrize(
    "maximum_cycles",
    [0, -1, True, "two"],
)
def test_invalid_maximum_cycles_are_rejected(
    maximum_cycles,
):
    """Cycle limits must be positive integers."""

    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        validate_runner_settings(
            interval_seconds=60,
            minimum_interval_seconds=60,
            maximum_cycles=maximum_cycles,
        )


def test_single_cycle_completes_without_sleeping(
    tmp_path,
):
    """A one-cycle run should finish immediately."""

    calls = []
    sleeps = []

    def cycle():
        calls.append("cycle")

    def fake_sleep(seconds):
        sleeps.append(seconds)

    status_path = tmp_path / "runner_status.json"

    status = run_autonomous_runner(
        cycle_callable=cycle,
        interval_seconds=60,
        minimum_interval_seconds=60,
        maximum_cycles=1,
        sleep_callable=fake_sleep,
        status_path=status_path,
    )

    assert calls == ["cycle"]
    assert sleeps == []
    assert status["status"] == "COMPLETED"
    assert status["cycles_completed"] == 1
    assert status["failures"] == 0
    assert status_path.exists()


def test_multiple_cycles_wait_between_runs(
    tmp_path,
):
    """Two cycles should contain one waiting period."""

    calls = []
    sleeps = []

    def cycle():
        calls.append("cycle")

    def fake_sleep(seconds):
        sleeps.append(seconds)

    status = run_autonomous_runner(
        cycle_callable=cycle,
        interval_seconds=60,
        minimum_interval_seconds=60,
        maximum_cycles=2,
        sleep_callable=fake_sleep,
        status_path=tmp_path / "status.json",
    )

    assert calls == ["cycle", "cycle"]
    assert sleeps == [60]
    assert status["cycles_completed"] == 2
    assert status["status"] == "COMPLETED"


def test_cycle_failure_is_recorded_and_stops_runner(
    tmp_path,
):
    """A failed cycle must stop and preserve the error."""

    def failing_cycle():
        raise RuntimeError("simulated cycle failure")

    status_path = tmp_path / "failure_status.json"

    status = run_autonomous_runner(
        cycle_callable=failing_cycle,
        interval_seconds=60,
        minimum_interval_seconds=60,
        maximum_cycles=3,
        sleep_callable=lambda seconds: None,
        status_path=status_path,
    )

    saved_status = json.loads(
        status_path.read_text(encoding="utf-8")
    )

    assert status["status"] == "FAILED"
    assert status["cycles_completed"] == 0
    assert status["failures"] == 1
    assert "simulated cycle failure" in (
        status["last_error"]
    )
    assert saved_status["status"] == "FAILED"


def test_keyboard_interrupt_stops_cleanly(
    tmp_path,
):
    """Control+C should produce a controlled stop."""

    def interrupted_cycle():
        raise KeyboardInterrupt

    status = run_autonomous_runner(
        cycle_callable=interrupted_cycle,
        interval_seconds=60,
        minimum_interval_seconds=60,
        maximum_cycles=None,
        sleep_callable=lambda seconds: None,
        status_path=tmp_path / "stopped.json",
    )

    assert status["status"] == "STOPPED"
    assert status["stopped_by_user"] is True
    assert status["failures"] == 0


def test_parser_defaults_to_one_cycle():
    """The command line should default to one cycle."""

    parser = build_argument_parser()
    arguments = parser.parse_args([])

    assert arguments.cycles == 1
    assert arguments.continuous is False
    assert arguments.interval is None


def test_parser_accepts_continuous_mode():
    """Continuous mode should be explicitly requested."""

    parser = build_argument_parser()
    arguments = parser.parse_args(
        [
            "--continuous",
            "--interval",
            "120",
        ]
    )

    assert arguments.continuous is True
    assert arguments.interval == 120