"""Verify maintenance progress lifecycle creation is failure-isolated."""

from unittest.mock import Mock, patch

import pytest

from himp.services.automation import AutomationService


@pytest.mark.parametrize(
    "task_id",
    [
        "scheduled_updates",
        "update_host",
        "update_group",
    ],
)
def test_maintenance_factory_preserves_attempt_and_owner(task_id):
    service = object.__new__(AutomationService)
    repository = Mock()

    with patch(
        "himp.services.automation.AutomationProgressRepository",
        return_value=repository,
    ):
        lifecycle = service._create_progress_lifecycle(
            task_id=task_id,
            attempt=2,
            execution_token="synthetic-owner-token",
        )

    assert lifecycle is not None
    assert lifecycle.repository is repository
    assert lifecycle.task_id == task_id
    assert lifecycle.attempt == 2
    assert lifecycle.execution_token == "synthetic-owner-token"


def test_nonmaintenance_task_does_not_create_repository():
    service = object.__new__(AutomationService)

    with patch(
        "himp.services.automation.AutomationProgressRepository"
    ) as repository:
        lifecycle = service._create_progress_lifecycle(
            task_id="health_check",
            attempt=1,
            execution_token="synthetic-owner-token",
        )

    assert lifecycle is None
    repository.assert_not_called()


def test_repository_initialization_failure_is_isolated():
    service = object.__new__(AutomationService)

    with patch(
        "himp.services.automation.AutomationProgressRepository",
        side_effect=RuntimeError(
            "Synthetic database initialization failure"
        ),
    ):
        lifecycle = service._create_progress_lifecycle(
            task_id="scheduled_updates",
            attempt=1,
            execution_token="synthetic-owner-token",
        )

    assert lifecycle is None


def test_each_attempt_gets_independent_lifecycle():
    service = object.__new__(AutomationService)

    with patch(
        "himp.services.automation.AutomationProgressRepository",
        return_value=Mock(),
    ):
        first = service._create_progress_lifecycle(
            "scheduled_updates",
            1,
            "synthetic-owner-token",
        )

        second = service._create_progress_lifecycle(
            "scheduled_updates",
            2,
            "synthetic-owner-token",
        )

    assert first is not second
    assert first.attempt == 1
    assert second.attempt == 2
    assert first.execution_token == second.execution_token
