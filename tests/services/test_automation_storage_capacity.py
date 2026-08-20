from himp.services.automation import AutomationService


class FakeStorage:

    def __init__(self):
        self.calls = []

    def collect_all(
        self,
        timeout=None,
    ):
        self.calls.append(
            timeout
        )

        return {
            "success": True,
            "hosts": 2,
            "filesystems": 4,
            "warning": 1,
            "critical": 0,
            "transitions": [],
        }


def test_storage_capacity_task_declares_daily_schedule():
    service = AutomationService()

    task = next(
        task
        for task in service.tasks
        if (
            task["id"]
            == "storage_capacity_check"
        )
    )

    assert task["enabled"] is True

    assert (
        task["schedule"]
        == "daily 04:15"
    )

    assert (
        task["risk_level"]
        == "read_only"
    )


def test_storage_capacity_task_executes_storage_service():
    service = AutomationService()

    storage = FakeStorage()

    service.storage = storage

    result = service._execute_task(
        "storage_capacity_check",
        timeout=900,
    )

    assert storage.calls == [
        900
    ]

    assert result["success"] is True
    assert result["hosts"] == 2
