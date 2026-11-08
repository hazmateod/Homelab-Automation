"""Verify progress finalization cannot change maintenance outcomes."""

from unittest.mock import Mock

import pytest

from tests.services.test_automation_policy import (
    FakeLockRepository,
    RecordingExecutionRepository,
    make_service,
)


def make_maintenance_service():
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

    return service, history, lock


@pytest.mark.parametrize("success", [True, False])
def test_finalization_exception_preserves_result_and_history(success):
    service, history, lock = make_maintenance_service()

    lifecycle = Mock()

    lifecycle.finalize_safely.side_effect = RuntimeError(
        "Synthetic progress finalization failure"
    )

    service._create_progress_lifecycle = (
        lambda task_id, attempt, token: lifecycle
    )

    calls = []

    def fake_execute(
        task_id,
        limit=None,
        timeout=None,
        progress_lifecycle=None,
    ):
        calls.append(task_id)

        assert progress_lifecycle is lifecycle

        return {"success": success}

    service._execute_task = fake_execute

    result = service.run(
        "update_host",
        limit="synthetic-host",
        confirmed=True,
    )

    assert result["attempt"] == 1
    assert len(calls) == 1

    assert len(history.saved) == 1
    assert history.saved[0]["success"] is success

    assert lock.release_calls == ["update_host"]

    lifecycle.finalize_safely.assert_called_once_with(
        success=success,
        execution_id=result["id"],
    )


def test_execution_exception_preserves_original_error():
    service, history, lock = make_maintenance_service()

    lifecycle = Mock()

    lifecycle.finalize_safely.side_effect = RuntimeError(
        "Synthetic progress finalization failure"
    )

    service._create_progress_lifecycle = (
        lambda task_id, attempt, token: lifecycle
    )

    def fake_execute(
        task_id,
        limit=None,
        timeout=None,
        progress_lifecycle=None,
    ):
        raise ValueError("Synthetic maintenance execution failure")

    service._execute_task = fake_execute

    with pytest.raises(
        ValueError,
        match="Synthetic maintenance execution failure",
    ):
        service.run(
            "update_host",
            limit="synthetic-host",
            confirmed=True,
        )

    assert len(history.saved) == 1
    assert history.saved[0]["success"] is False

    assert lock.release_calls == ["update_host"]

    lifecycle.finalize_safely.assert_called_once()
    assert (
        lifecycle.finalize_safely.call_args.kwargs["success"]
        is False
    )
