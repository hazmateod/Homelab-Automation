import pytest

from himp.services.automation import (
    AutomationConfirmationRequiredError,
    AutomationDependencyNotSatisfiedError,
    AutomationDisabledError,
    AutomationService,
)


class FakeDependencyRepository:
    def __init__(self, dependencies=None):
        self.dependencies = dependencies or {}

    def list(self, task_id):
        return [
            {
                "task_id": task_id,
                "depends_on_task_id": dependency,
            }
            for dependency in self.dependencies.get(
                task_id,
                [],
            )
        ]


class FakeExecutionRepository:
    def __init__(self, executions=None):
        self.executions = executions or {}

    def latest(self, task_id):
        return self.executions.get(task_id)


def make_service():
    service = object.__new__(AutomationService)

    service.tasks = [
        {
            "id": "health_check",
            "name": "Health Check",
            "description": "Test health task.",
            "enabled": True,
            "schedule": "manual",
            "timeout_seconds": 300,
            "retry_attempts": 1,
            "retry_delay_seconds": 0,
            "risk_level": "read_only",
        },
        {
            "id": "dependent_task",
            "name": "Dependent Task",
            "description": "Test dependent task.",
            "enabled": True,
            "schedule": "manual",
            "timeout_seconds": 300,
            "retry_attempts": 1,
            "retry_delay_seconds": 0,
            "risk_level": "read_only",
        },
        {
            "id": "maintenance_task",
            "name": "Maintenance Task",
            "description": "Test maintenance task.",
            "enabled": True,
            "schedule": "manual",
            "timeout_seconds": 300,
            "retry_attempts": 1,
            "retry_delay_seconds": 0,
            "risk_level": "maintenance",
        },
    ]

    service.dependency_repository = (
        FakeDependencyRepository()
    )
    service.execution_repository = (
        FakeExecutionRepository()
    )

    return service


def test_enabled_task_policy_is_allowed():
    service = make_service()

    policy = service.validate_execution_policy(
        "health_check"
    )

    assert policy["task_id"] == "health_check"
    assert policy["enabled"] is True
    assert policy["risk_level"] == "read_only"
    assert policy["confirmed"] is False
    assert policy["retry_attempts"] == 1
    assert policy["retry_delay_seconds"] == 0
    assert policy["timeout_seconds"] == 300
    assert policy["dependencies"] == []


def test_disabled_task_policy_is_rejected():
    service = make_service()

    service.find_task(
        "health_check"
    )["enabled"] = False

    with pytest.raises(
        AutomationDisabledError,
        match="Automation task is disabled",
    ):
        service.validate_execution_policy(
            "health_check"
        )


def test_missing_dependency_policy_is_rejected():
    service = make_service()

    service.dependency_repository = (
        FakeDependencyRepository(
            {
                "dependent_task": [
                    "health_check",
                ],
            }
        )
    )

    with pytest.raises(
        AutomationDependencyNotSatisfiedError,
        match="never completed successfully",
    ):
        service.validate_execution_policy(
            "dependent_task"
        )


def test_failed_dependency_policy_is_rejected():
    service = make_service()

    service.dependency_repository = (
        FakeDependencyRepository(
            {
                "dependent_task": [
                    "health_check",
                ],
            }
        )
    )

    service.execution_repository = (
        FakeExecutionRepository(
            {
                "health_check": {
                    "success": False,
                },
            }
        )
    )

    with pytest.raises(
        AutomationDependencyNotSatisfiedError,
        match="dependency failed",
    ):
        service.validate_execution_policy(
            "dependent_task"
        )


def test_successful_dependency_policy_is_allowed():
    service = make_service()

    service.dependency_repository = (
        FakeDependencyRepository(
            {
                "dependent_task": [
                    "health_check",
                ],
            }
        )
    )

    service.execution_repository = (
        FakeExecutionRepository(
            {
                "health_check": {
                    "success": True,
                },
            }
        )
    )

    policy = service.validate_execution_policy(
        "dependent_task"
    )

    assert policy["task_id"] == "dependent_task"
    assert len(policy["dependencies"]) == 1
    assert policy["dependencies"][0][
        "depends_on_task_id"
    ] == "health_check"


def test_destructive_task_requires_confirmation():
    service = make_service()

    service.find_task(
        "maintenance_task"
    )["risk_level"] = "destructive"

    with pytest.raises(
        AutomationConfirmationRequiredError,
        match="requires explicit confirmation",
    ):
        service.validate_execution_policy(
            "maintenance_task"
        )


def test_destructive_task_with_confirmation_is_allowed():
    service = make_service()

    service.find_task(
        "maintenance_task"
    )["risk_level"] = "destructive"

    policy = service.validate_execution_policy(
        "maintenance_task",
        confirmed=True,
    )

    assert policy["task_id"] == "maintenance_task"
    assert policy["risk_level"] == "destructive"
    assert policy["confirmed"] is True


def test_invalid_retry_attempts_are_rejected():
    service = make_service()

    service.find_task(
        "health_check"
    )["retry_attempts"] = 0

    with pytest.raises(
        ValueError,
        match="retry_attempts",
    ):
        service.validate_execution_policy(
            "health_check"
        )


def test_invalid_retry_delay_is_rejected():
    service = make_service()

    service.find_task(
        "health_check"
    )["retry_delay_seconds"] = -1

    with pytest.raises(
        ValueError,
        match="retry_delay_seconds",
    ):
        service.validate_execution_policy(
            "health_check"
        )


def test_invalid_timeout_is_rejected():
    service = make_service()

    service.find_task(
        "health_check"
    )["timeout_seconds"] = 0

    with pytest.raises(
        ValueError,
        match="timeout_seconds",
    ):
        service.validate_execution_policy(
            "health_check"
        )


def test_valid_policy_returns_retry_and_timeout_configuration():
    service = make_service()

    task = service.find_task(
        "health_check"
    )

    task["retry_attempts"] = 3
    task["retry_delay_seconds"] = 5
    task["timeout_seconds"] = 600

    policy = service.validate_execution_policy(
        "health_check"
    )

    assert policy["retry_attempts"] == 3
    assert policy["retry_delay_seconds"] == 5
    assert policy["timeout_seconds"] == 600


class FakeLockRepository:
    def __init__(self, acquire_result=True):
        self.acquire_result = acquire_result
        self.acquire_calls = []
        self.release_calls = []

    def acquire(self, task_id):
        self.acquire_calls.append(task_id)
        return self.acquire_result

    def release(self, task_id):
        self.release_calls.append(task_id)


class RecordingExecutionRepository:
    def __init__(self):
        self.saved = []

    def save(
        self,
        task_id,
        success,
        elapsed,
        result,
        executed_at=None,
    ):
        self.saved.append(
            {
                "task_id": task_id,
                "success": success,
                "elapsed": elapsed,
                "result": result,
                "executed_at": executed_at,
            }
        )


def test_disabled_execution_does_not_acquire_lock():
    service = make_service()

    service.find_task(
        "health_check"
    )["enabled"] = False

    service.lock_repository = FakeLockRepository()

    with pytest.raises(
        AutomationDisabledError
    ):
        service.run(
            "health_check"
        )

    assert service.lock_repository.acquire_calls == []


def test_dependency_failure_does_not_acquire_lock():
    service = make_service()

    service.dependency_repository = (
        FakeDependencyRepository(
            {
                "dependent_task": [
                    "health_check",
                ],
            }
        )
    )

    service.execution_repository = (
        FakeExecutionRepository(
            {
                "health_check": {
                    "success": False,
                },
            }
        )
    )

    service.lock_repository = FakeLockRepository()

    with pytest.raises(
        AutomationDependencyNotSatisfiedError
    ):
        service.run(
            "dependent_task"
        )

    assert service.lock_repository.acquire_calls == []


def test_confirmation_failure_does_not_acquire_lock():
    service = make_service()

    service.find_task(
        "maintenance_task"
    )["risk_level"] = "destructive"

    service.lock_repository = FakeLockRepository()

    with pytest.raises(
        AutomationConfirmationRequiredError
    ):
        service.run(
            "maintenance_task"
        )

    assert service.lock_repository.acquire_calls == []


def test_successful_execution_acquires_and_releases_lock():
    service = make_service()

    lock = FakeLockRepository()
    history = RecordingExecutionRepository()

    service.lock_repository = lock
    service.execution_repository = history

    executed = []

    def fake_execute_task(
        task_id,
        limit=None,
        timeout=None,
    ):
        executed.append(
            {
                "task_id": task_id,
                "limit": limit,
                "timeout": timeout,
            }
        )

        return {
            "success": True,
            "message": "test execution",
        }

    service._execute_task = fake_execute_task

    result = service.run(
        "health_check"
    )

    assert result["task"] == "health_check"

    assert executed == [
        {
            "task_id": "health_check",
            "limit": None,
            "timeout": 300,
        }
    ]

    assert lock.acquire_calls == [
        "health_check"
    ]

    assert lock.release_calls == [
        "health_check"
    ]

    assert len(history.saved) == 1
    assert history.saved[0]["task_id"] == "health_check"
    assert history.saved[0]["success"] is True


def test_execution_failure_still_releases_lock():
    service = make_service()

    lock = FakeLockRepository()
    history = RecordingExecutionRepository()

    service.lock_repository = lock
    service.execution_repository = history

    def fake_execute_task(
        task_id,
        limit=None,
        timeout=None,
    ):
        raise RuntimeError(
            "simulated execution failure"
        )

    service._execute_task = fake_execute_task

    with pytest.raises(
        RuntimeError,
        match="simulated execution failure",
    ):
        service.run(
            "health_check"
        )

    assert lock.acquire_calls == [
        "health_check"
    ]

    assert lock.release_calls == [
        "health_check"
    ]

    assert len(history.saved) == 1
    assert history.saved[0]["success"] is False
