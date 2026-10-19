"""Safely run governed Aureus cycles on a schedule."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from src.agent_cycle import main as run_one_agent_cycle
from src.config_loader import load_policy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER_STATUS_PATH = (
    PROJECT_ROOT
    / "data"
    / "state"
    / "autonomous_runner_status.json"
)


def current_utc_timestamp() -> str:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


def create_runner_status(
    interval_seconds: int,
    maximum_cycles: int | None,
) -> dict[str, Any]:
    """Create the initial autonomous-runner state."""

    return {
        "schema_version": "1.0",
        "runner_type": "governed_autonomous_sandbox",
        "status": "STARTING",
        "started_at": current_utc_timestamp(),
        "updated_at": current_utc_timestamp(),
        "completed_at": None,
        "interval_seconds": interval_seconds,
        "maximum_cycles": maximum_cycles,
        "cycles_completed": 0,
        "failures": 0,
        "last_cycle_started_at": None,
        "last_cycle_completed_at": None,
        "last_error": None,
        "stopped_by_user": False,
        "uses_real_money": False,
    }


def save_runner_status(
    status: dict[str, Any],
    file_path: Path = RUNNER_STATUS_PATH,
) -> None:
    """Save the runner's current operational state."""

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with file_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(status, file, indent=2)


def validate_runner_settings(
    interval_seconds: int,
    minimum_interval_seconds: int,
    maximum_cycles: int | None,
) -> None:
    """Validate runner settings against policy limits."""

    if (
        not isinstance(interval_seconds, int)
        or isinstance(interval_seconds, bool)
    ):
        raise ValueError(
            "The cycle interval must be an integer."
        )

    if (
        not isinstance(minimum_interval_seconds, int)
        or isinstance(minimum_interval_seconds, bool)
        or minimum_interval_seconds <= 0
    ):
        raise ValueError(
            "The policy minimum interval is invalid."
        )

    if interval_seconds < minimum_interval_seconds:
        raise ValueError(
            "The requested interval is below the policy minimum."
        )

    if maximum_cycles is not None:
        if (
            not isinstance(maximum_cycles, int)
            or isinstance(maximum_cycles, bool)
            or maximum_cycles <= 0
        ):
            raise ValueError(
                "Maximum cycles must be a positive integer."
            )


def run_autonomous_runner(
    cycle_callable: Callable[[], None],
    interval_seconds: int,
    minimum_interval_seconds: int,
    maximum_cycles: int | None,
    sleep_callable: Callable[[float], None] = time.sleep,
    status_path: Path = RUNNER_STATUS_PATH,
) -> dict[str, Any]:
    """Run governed cycles until completion, failure, or interruption."""

    validate_runner_settings(
        interval_seconds=interval_seconds,
        minimum_interval_seconds=minimum_interval_seconds,
        maximum_cycles=maximum_cycles,
    )

    status = create_runner_status(
        interval_seconds=interval_seconds,
        maximum_cycles=maximum_cycles,
    )
    status["status"] = "RUNNING"
    status["updated_at"] = current_utc_timestamp()
    save_runner_status(status, status_path)

    try:
        while (
            maximum_cycles is None
            or status["cycles_completed"] < maximum_cycles
        ):
            status["last_cycle_started_at"] = (
                current_utc_timestamp()
            )
            status["updated_at"] = current_utc_timestamp()
            save_runner_status(status, status_path)

            try:
                cycle_callable()
            except Exception as error:
                status["failures"] += 1
                status["last_error"] = (
                    f"{type(error).__name__}: {error}"
                )
                status["status"] = "FAILED"
                status["updated_at"] = (
                    current_utc_timestamp()
                )
                status["completed_at"] = (
                    current_utc_timestamp()
                )
                save_runner_status(
                    status,
                    status_path,
                )
                break

            status["cycles_completed"] += 1
            status["last_cycle_completed_at"] = (
                current_utc_timestamp()
            )
            status["updated_at"] = current_utc_timestamp()
            save_runner_status(status, status_path)

            if (
                maximum_cycles is not None
                and status["cycles_completed"]
                >= maximum_cycles
            ):
                status["status"] = "COMPLETED"
                break

            print()
            print(
                "Aureus is waiting "
                f"{interval_seconds} seconds "
                "before the next cycle."
            )
            print(
                "Press Control+C to stop safely."
            )

            sleep_callable(interval_seconds)

    except KeyboardInterrupt:
        status["status"] = "STOPPED"
        status["stopped_by_user"] = True
        status["last_error"] = None

    if status["status"] == "RUNNING":
        status["status"] = "COMPLETED"

    if status["completed_at"] is None:
        status["completed_at"] = current_utc_timestamp()

    status["updated_at"] = current_utc_timestamp()
    save_runner_status(status, status_path)

    return status


def print_runner_summary(
    status: dict[str, Any],
) -> None:
    """Display the runner's final state."""

    print()
    print("Aureus autonomous runner")
    print("========================")
    print(f"Status: {status['status']}")
    print(
        "Cycles completed: "
        f"{status['cycles_completed']}"
    )
    print(f"Failures: {status['failures']}")
    print(
        "Interval: "
        f"{status['interval_seconds']} seconds"
    )
    print(
        "Stopped by user: "
        f"{status['stopped_by_user']}"
    )
    print(
        "Real money enabled: "
        f"{status['uses_real_money']}"
    )

    if status["last_error"] is not None:
        print(
            "Last error: "
            f"{status['last_error']}"
        )

    print()
    print(
        f"Runner status saved to: "
        f"{RUNNER_STATUS_PATH}"
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Run Aureus autonomous sandbox cycles."
        )
    )

    mode_group = parser.add_mutually_exclusive_group()

    mode_group.add_argument(
        "--cycles",
        type=int,
        default=1,
        help=(
            "Number of cycles to run. "
            "The default is one."
        ),
    )

    mode_group.add_argument(
        "--continuous",
        action="store_true",
        help=(
            "Run continuously until Control+C."
        ),
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help=(
            "Seconds between cycles. "
            "Cannot be below the policy minimum."
        ),
    )

    return parser


def main() -> None:
    """Run the autonomous sandbox scheduler."""

    arguments = build_argument_parser().parse_args()
    policy = load_policy()

    minimum_interval_seconds = policy[
        "operational_limits"
    ]["minimum_seconds_between_cycles"]

    interval_seconds = (
        minimum_interval_seconds
        if arguments.interval is None
        else arguments.interval
    )

    maximum_cycles = (
        None
        if arguments.continuous
        else arguments.cycles
    )

    print("Starting Aureus autonomous runner.")
    print(
        "Mode: "
        f"{policy['operating_mode']}"
    )
    print(
        "Financial activity: simulation only"
    )
    print(
        "Cycle interval: "
        f"{interval_seconds} seconds"
    )

    status = run_autonomous_runner(
        cycle_callable=run_one_agent_cycle,
        interval_seconds=interval_seconds,
        minimum_interval_seconds=(
            minimum_interval_seconds
        ),
        maximum_cycles=maximum_cycles,
    )

    print_runner_summary(status)


if __name__ == "__main__":
    main()