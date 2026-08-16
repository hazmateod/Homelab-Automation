import pytest

from himp.services.automation import (
    AutomationAlreadyRunningError,
    AutomationConfirmationRequiredError,
    AutomationDependencyCycleError,
    AutomationDependencyNotFoundError,
    AutomationDependencyNotSatisfiedError,
    AutomationDisabledError,
    AutomationService,
)


@pytest.mark.parametrize(
    "error,category,retryable",
    [
        (
            TimeoutError("timed out"),
            "timeout",
            True,
        ),
        (
            OSError("connection refused"),
            "unreachable",
            True,
        ),
        (
            RuntimeError("execution failed"),
            "execution",
            True,
        ),
        (
            ValueError("unexpected value"),
            "internal",
            False,
        ),
        (
            Exception("unexpected failure"),
            "internal",
            False,
        ),
    ],
)
def test_classify_error_returns_expected_category(
    error,
    category,
    retryable,
):
    result = AutomationService._classify_error(
        error
    )

    assert result == {
        "category": category,
        "retryable": retryable,
    }


def test_non_retryable_failure_is_not_retried():
    service = object.__new__(AutomationService)

    service.tasks = [
        {
            "id": "health_check",
            "name": "Health Check",
            "description": "Test health task.",
            "enabled": True,
            "schedule": "manual",
            "timeout_seconds": 300,
            "retry_attempts": 3,
            "retry_delay_seconds": 0,
            "risk_level": "read_only",
        },
    ]

    class FakeDependencyRepository:
        def list(self, task_id):
            return []

    class FakeLockRepository:
        def acquire(
            self,
            task_id,
            lease_seconds=None,
        ):
            return True

        def release(self, task_id):
            return None

    class FakeExecutionRepository:
        def __init__(self):
            self.saved = []

        def save(
            self,
            task_id,
            success,
            elapsed,
            result,
            executed_at=None,
            workflow_execution_id=None,
        ):
            self.saved.append(result)
            return len(self.saved)

    service.dependency_repository = (
        FakeDependencyRepository()
    )
    service.lock_repository = (
        FakeLockRepository()
    )
    service.execution_repository = (
        FakeExecutionRepository()
    )

    calls = []

    def fake_execute_task(
        task_id,
        limit=None,
        timeout=None,
    ):
        calls.append(task_id)

        raise ValueError(
            "non-retryable configuration failure"
        )

    service._execute_task = fake_execute_task

    with pytest.raises(
        ValueError,
        match="non-retryable configuration failure",
    ):
        service.run(
            "health_check"
        )

    assert calls == [
        "health_check",
    ]

    assert len(
        service.execution_repository.saved
    ) == 1

@pytest.mark.parametrize(
    "error,category,retryable",
    [
        (
            AutomationAlreadyRunningError(
                "already running"
            ),
            "concurrency",
            False,
        ),
        (
            AutomationDisabledError(
                "disabled"
            ),
            "disabled",
            False,
        ),
        (
            AutomationConfirmationRequiredError(
                "confirmation required"
            ),
            "confirmation",
            False,
        ),
        (
            AutomationDependencyNotSatisfiedError(
                "dependency not satisfied"
            ),
            "dependency",
            False,
        ),
        (
            AutomationDependencyNotFoundError(
                "dependency not found"
            ),
            "dependency",
            False,
        ),
        (
            AutomationDependencyCycleError(
                "dependency cycle"
            ),
            "dependency",
            False,
        ),
    ],
)
def test_classify_automation_policy_errors_as_non_retryable(
    error,
    category,
    retryable,
):
    result = AutomationService._classify_error(
        error
    )

    assert result == {
        "category": category,
        "retryable": retryable,
    }
