"""Synthetic tests for maintenance progress retry isolation."""

from unittest.mock import Mock, patch

from himp.services.automation import AutomationService
from tests.services.test_automation_policy import (
    FakeLockRepository,
    RecordingExecutionRepository,
    make_service,
)


def test_retries_create_independent_progress_lifecycles():
    service = make_service()

    service.tasks.append({
        "id": "update_host",
        "name": "Update Host",
        "description": "Synthetic maintenance",
        "enabled": True,
        "schedule": "manual",
        "timeout_seconds": 60,
        "retry_attempts": 2,
        "retry_delay_seconds": 0,
        "risk_level": "maintenance",
    })

    history = RecordingExecutionRepository()
    lock = FakeLockRepository()

    service.execution_repository = history
    service.lock_repository = lock

    lifecycles = []
    executions = []

    def fake_factory(task_id, attempt, execution_token):
        lifecycle = Mock()
        lifecycle.task_id = task_id
        lifecycle.attempt = attempt
        lifecycle.execution_token = execution_token
        lifecycles.append(lifecycle)
        return lifecycle

    def fake_execute(
        task_id,
        limit=None,
        timeout=None,
        progress_lifecycle=None,
    ):
        executions.append({
            "task_id": task_id,
            "limit": limit,
            "lifecycle": progress_lifecycle,
        })

        return {
            "success": len(executions) == 2,
        }

    service._create_progress_lifecycle = fake_factory
    service._execute_task = fake_execute

    with patch("himp.services.automation.time.sleep"):
        result = service.run(
            "update_host",
            limit="synthetic-host",
            confirmed=True,
        )

    assert result["attempt"] == 2
    assert len(executions) == 2
    assert len(lifecycles) == 2
    assert lifecycles[0] is not lifecycles[1]

    assert lifecycles[0].attempt == 1
    assert lifecycles[1].attempt == 2

    assert (
        lifecycles[0].execution_token
        == lifecycles[1].execution_token
        == lock.execution_token
    )

    assert executions[0]["lifecycle"] is lifecycles[0]
    assert executions[1]["lifecycle"] is lifecycles[1]

    assert len(history.saved) == 2
    assert history.saved[0]["success"] is False
    assert history.saved[1]["success"] is True

    assert lock.release_calls == ["update_host"]


def test_progress_factory_failure_does_not_block_maintenance():
    service = make_service()

    service.tasks.append({
        "id": "update_host",
        "name": "Update Host",
        "description": "Synthetic maintenance",
        "enabled": True,
        "schedule": "manual",
        "timeout_seconds": 60,
        "retry_attempts": 1,
        "retry_delay_seconds": 0,
        "risk_level": "maintenance",
    })

    history = RecordingExecutionRepository()
    lock = FakeLockRepository()

    service.execution_repository = history
    service.lock_repository = lock

    executed = []

    def fake_execute(
        task_id,
        limit=None,
        timeout=None,
    ):
        executed.append(task_id)
        return {"success": True}

    service._execute_task = fake_execute

    with patch(
        "himp.services.automation.AutomationProgressRepository",
        side_effect=RuntimeError(
            "Synthetic progress database failure"
        ),
    ):
        result = service.run(
            "update_host",
            limit="synthetic-host",
            confirmed=True,
        )

    assert result["attempt"] == 1
    assert executed == ["update_host"]
    assert len(history.saved) == 1
    assert history.saved[0]["success"] is True
    assert lock.release_calls == ["update_host"]
