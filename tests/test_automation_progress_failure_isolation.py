"""Verify progress persistence failures cannot alter execution outcomes."""

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
        execution_token="synthetic-owner-token",
    )

    return lifecycle, repository


def test_successful_finalization():
    lifecycle, repository = make_lifecycle()

    lifecycle.start(["host01"])

    assert lifecycle.finalize_safely(
        success=True,
        execution_id=123,
    ) is True

    repository.update.assert_called_once_with(
        "synthetic-run-id",
        status="succeeded",
        completed_execution_id=123,
        execution_token="synthetic-owner-token",
    )


def test_database_failure_is_isolated():
    lifecycle, repository = make_lifecycle()

    lifecycle.start(["host01"])

    repository.update.side_effect = RuntimeError(
        "Synthetic database failure"
    )

    assert lifecycle.finalize_safely(
        success=True,
        execution_id=123,
    ) is False

    repository.update.assert_called_once()


def test_unstarted_lifecycle_is_safe():
    lifecycle, repository = make_lifecycle()

    assert lifecycle.finalize_safely(
        success=False,
        execution_id=456,
    ) is False

    repository.update.assert_not_called()


def test_failed_execution_finalizes_as_failed():
    lifecycle, repository = make_lifecycle()

    lifecycle.start(["host01"])

    assert lifecycle.finalize_safely(
        success=False,
        execution_id=789,
    ) is True

    repository.update.assert_called_once_with(
        "synthetic-run-id",
        status="failed",
        completed_execution_id=789,
        execution_token="synthetic-owner-token",
    )
