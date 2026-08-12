from himp.services.automation import AutomationService


class FakeDependencyRepository:
    def list(self, task_id):
        return []


class FakeLockRepository:
    def acquire(self, task_id):
        return True

    def release(self, task_id):
        return None


class FakeExecutionRepository:
    def __init__(self):
        self.saved = []
        self.next_id = 42

    def save(
        self,
        task_id,
        success,
        elapsed,
        result,
        executed_at=None,
    ):
        execution_id = self.next_id
        self.next_id += 1

        self.saved.append(
            {
                "id": execution_id,
                "task_id": task_id,
                "success": success,
                "elapsed": elapsed,
                "result": result,
                "executed_at": executed_at,
            }
        )

        return execution_id

    def find(self, execution_id):
        for execution in self.saved:
            if execution["id"] == execution_id:
                return execution

        return None


class FakeHealthService:
    def summary(self):
        return {
            "success": True,
            "status": "healthy",
        }


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
    ]

    service.dependency_repository = (
        FakeDependencyRepository()
    )

    service.execution_repository = (
        FakeExecutionRepository()
    )

    service.lock_repository = (
        FakeLockRepository()
    )

    service.health = FakeHealthService()
    service.reports = None
    service.inventory = None
    service.updates = None
    service.host_health = None

    return service


def test_run_returns_persisted_execution_id():
    service = make_service()

    execution = service.run(
        "health_check"
    )

    assert execution["id"] == 42

    persisted = (
        service.execution_repository.find(
            execution["id"]
        )
    )

    assert persisted is not None
    assert persisted["id"] == execution["id"]
    assert persisted["task_id"] == "health_check"
    assert persisted["success"] is True


def test_run_persists_failure_classification():
    service = make_service()

    service.health.summary = lambda: (
        (_ for _ in ()).throw(
            OSError("connection refused")
        )
    )

    service.tasks[0]["retry_attempts"] = 1

    try:
        service.run(
            "health_check"
        )
    except OSError:
        pass
    else:
        raise AssertionError(
            "Expected OSError from failed automation."
        )

    assert len(
        service.execution_repository.saved
    ) == 1

    persisted = (
        service.execution_repository.saved[0]
    )

    assert persisted["success"] is False

    result = persisted["result"]["result"]

    assert result["error"] == "connection refused"
    assert result["error_category"] == "unreachable"
    assert result["retryable"] is True


def test_retry_attempts_persist_individual_execution_records():
    service = make_service()

    service.tasks[0]["retry_attempts"] = 2

    calls = []

    def fake_execute_task(
        task_id,
        limit=None,
        timeout=None,
    ):
        calls.append(task_id)

        if len(calls) == 1:
            raise RuntimeError(
                "transient failure"
            )

        return {
            "success": True,
            "message": "recovered",
        }

    service._execute_task = fake_execute_task

    execution = service.run(
        "health_check"
    )

    saved = service.execution_repository.saved

    assert len(saved) == 2

    assert saved[0]["success"] is False
    assert saved[0]["result"]["attempt"] == 1
    assert saved[0]["result"]["attempts"] == 2
    assert (
        saved[0]["result"]["result"]["error"]
        == "transient failure"
    )

    assert saved[1]["success"] is True
    assert saved[1]["result"]["attempt"] == 2
    assert saved[1]["result"]["attempts"] == 2

    assert execution["id"] == saved[1]["id"]
    assert execution["attempt"] == 2
    assert execution["attempts"] == 2
    assert execution["result"]["success"] is True
