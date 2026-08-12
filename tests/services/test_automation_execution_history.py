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
