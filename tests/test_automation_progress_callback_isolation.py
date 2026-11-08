"""Verify maintenance progress callbacks isolate persistence failures."""

from unittest.mock import Mock

from himp.services.automation_progress_lifecycle import (
    AutomationProgressLifecycle,
)


def make_lifecycle():
    repository = Mock()
    repository.start.return_value = "synthetic-run-id"

    lifecycle = AutomationProgressLifecycle(
        repository,
        task_id="scheduled_updates",
        attempt=1,
        execution_token="synthetic-owner",
    )

    return lifecycle, repository


def test_successful_safe_start():
    lifecycle, repository = make_lifecycle()

    assert lifecycle.start_safely(["host01"], []) == (
        "synthetic-run-id"
    )

    assert lifecycle.run_id == "synthetic-run-id"
    assert lifecycle.tracker is not None

    repository.start.assert_called_once()


def test_initialization_failure_is_isolated():
    lifecycle, repository = make_lifecycle()

    repository.start.side_effect = RuntimeError(
        "Synthetic initialization failure"
    )

    assert lifecycle.start_safely(["host01"], []) is None
    assert lifecycle.tracker is None
    assert lifecycle.run_id is None


def test_event_failure_is_isolated():
    lifecycle, repository = make_lifecycle()

    lifecycle.start_safely(["host01"], [])

    repository.get.side_effect = RuntimeError(
        "Synthetic event persistence failure"
    )

    event = {
        "event": "task_ok",
        "host": "host01",
        "task": "Synthetic test",
        "changed": False,
    }

    assert lifecycle.handle_event_safely(event) is False
    assert lifecycle.tracker is None


def test_events_after_failure_are_ignored():
    lifecycle, repository = make_lifecycle()

    lifecycle.start_safely(["host01"], [])

    repository.get.side_effect = RuntimeError(
        "Synthetic persistence failure"
    )

    lifecycle.handle_event_safely(
        {
            "event": "task_ok",
            "host": "host01",
        }
    )

    repository.get.reset_mock()

    assert lifecycle.handle_event_safely({}) is False
    repository.get.assert_not_called()


def test_unstarted_event_is_ignored():
    lifecycle, repository = make_lifecycle()

    assert lifecycle.handle_event_safely({}) is False

    repository.get.assert_not_called()
