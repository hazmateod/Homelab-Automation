import pytest

from fastapi import HTTPException

from himp.api import automation


class FakeExecutionRepository:
    def __init__(self, history=None):
        self._history = history or []

    def history(
        self,
        limit=50,
        task_id=None,
        success=None,
    ):
        result = self._history

        if task_id is not None:
            result = [
                item
                for item in result
                if item["task_id"] == task_id
            ]

        if success is not None:
            result = [
                item
                for item in result
                if item["success"] is success
            ]

        return result[:limit]

    def find(self, execution_id):
        for item in self._history:
            if item["id"] == execution_id:
                return item

        return None

    def task_history(
        self,
        task_id,
        limit=50,
    ):
        return [
            item
            for item in self._history
            if item["task_id"] == task_id
        ][:limit]


class FakeAutomation:
    def __init__(self):
        self.execution_repository = FakeExecutionRepository(
            [
                {
                    "id": 7,
                    "task_id": "health_check",
                    "success": True,
                    "elapsed": 1.25,
                    "result": {
                        "success": True,
                        "message": "healthy",
                    },
                    "executed_at": (
                        "2026-08-11T20:00:00+00:00"
                    ),
                },
                {
                    "id": 8,
                    "task_id": "health_check",
                    "success": False,
                    "elapsed": 2.50,
                    "result": {
                        "success": False,
                        "error": "health check failed",
                    },
                    "executed_at": (
                        "2026-08-11T20:01:00+00:00"
                    ),
                },
                {
                    "id": 9,
                    "task_id": "generate_reports",
                    "success": True,
                    "elapsed": 4.75,
                    "result": {
                        "success": True,
                        "message": "reports generated",
                    },
                    "executed_at": (
                        "2026-08-11T20:02:00+00:00"
                    ),
                },
            ]
        )


class FakeHIMP:
    def __init__(self):
        self.automation = FakeAutomation()


def test_execution_history_returns_records(monkeypatch):
    monkeypatch.setattr(
        automation,
        "himp",
        FakeHIMP(),
    )

    response = automation.automation_execution_history(
        limit=50,
        task_id=None,
        success=None,
    )

    import json

    body = json.loads(
        response.body
    )

    assert response.status_code == 200
    assert len(body) == 3

    assert [item["id"] for item in body] == [
        7,
        8,
        9,
    ]

    assert [item["task_id"] for item in body] == [
        "health_check",
        "health_check",
        "generate_reports",
    ]

    assert [item["success"] for item in body] == [
        True,
        False,
        True,
    ]

    assert body[0]["result"] == {
        "success": True,
        "message": "healthy",
    }

    assert body[1]["result"] == {
        "success": False,
        "error": "health check failed",
    }

    assert body[2]["result"] == {
        "success": True,
        "message": "reports generated",
    }


def test_execution_detail_returns_record(monkeypatch):
    monkeypatch.setattr(
        automation,
        "himp",
        FakeHIMP(),
    )

    response = automation.automation_execution_detail(
        7
    )

    import json

    body = json.loads(response.body)

    assert response.status_code == 200
    assert body["id"] == 7
    assert body["task_id"] == "health_check"
    assert body["success"] is True
    assert body["elapsed"] == 1.25
    assert body["result"] == {
        "success": True,
        "message": "healthy",
    }


def test_execution_detail_missing_record_returns_404(
    monkeypatch,
):
    monkeypatch.setattr(
        automation,
        "himp",
        FakeHIMP(),
    )

    with pytest.raises(
        Exception
    ) as captured:
        automation.automation_execution_detail(
            999
        )

    assert captured.value.status_code == 404


def test_task_execution_history_returns_task_records(
    monkeypatch,
):
    monkeypatch.setattr(
        automation,
        "himp",
        FakeHIMP(),
    )

    response = (
        automation.automation_task_execution_history(
            "health_check"
        )
    )

    import json

    body = json.loads(response.body)

    assert response.status_code == 200
    assert body["task_id"] == "health_check"
    assert body["count"] == 2
    assert [
        item["id"]
        for item in body["history"]
    ] == [
        7,
        8,
    ]
    assert all(
        item["task_id"] == "health_check"
        for item in body["history"]
    )


def test_task_execution_history_missing_task_returns_404(
    monkeypatch,
):
    monkeypatch.setattr(
        automation,
        "himp",
        FakeHIMP(),
    )

    with pytest.raises(
        Exception
    ) as captured:
        automation.automation_task_execution_history(
            "missing_task"
        )

    assert captured.value.status_code == 404


def test_execution_history_filters_by_task_id(
    monkeypatch,
):
    monkeypatch.setattr(
        automation,
        "himp",
        FakeHIMP(),
    )

    response = automation.automation_execution_history(
        limit=50,
        task_id="health_check",
        success=None,
    )

    import json

    body = json.loads(response.body)

    assert response.status_code == 200
    assert [item["id"] for item in body] == [
        7,
        8,
    ]
    assert all(
        item["task_id"] == "health_check"
        for item in body
    )


def test_execution_history_filters_by_success(
    monkeypatch,
):
    monkeypatch.setattr(
        automation,
        "himp",
        FakeHIMP(),
    )

    response = automation.automation_execution_history(
        limit=50,
        task_id=None,
        success=True,
    )

    import json

    body = json.loads(response.body)

    assert response.status_code == 200
    assert [item["id"] for item in body] == [
        7,
        9,
    ]
    assert all(
        item["success"] is True
        for item in body
    )


def test_execution_history_applies_limit(
    monkeypatch,
):
    monkeypatch.setattr(
        automation,
        "himp",
        FakeHIMP(),
    )

    response = automation.automation_execution_history(
        limit=1,
        task_id=None,
        success=None,
    )

    import json

    body = json.loads(response.body)

    assert response.status_code == 200
    assert len(body) == 1
    assert body[0]["id"] == 7


def test_run_automation_returns_successful_execution(monkeypatch):
    class FakeAutomation:
        def __init__(self):
            self.received_task_id = None
            self.received_confirmed = None

        def run(self, task_id, confirmed=False):
            self.received_task_id = task_id
            self.received_confirmed = confirmed

            return {
                "id": 42,
                "task": task_id,
                "success": True,
                "attempt": 1,
                "result": {
                    "success": True,
                    "message": "test execution",
                },
            }

    class FakeHIMP:
        def __init__(self):
            self.automation = FakeAutomation()

    fake_himp = FakeHIMP()

    monkeypatch.setattr(
        automation,
        "himp",
        fake_himp,
    )

    response = automation.run_automation(
        "health_check",
        automation.AutomationRunRequest(
            confirmed=True,
        ),
    )

    import json

    body = json.loads(response.body)

    assert response.status_code == 200

    assert body == {
        "id": 42,
        "task": "health_check",
        "success": True,
        "attempt": 1,
        "result": {
            "success": True,
            "message": "test execution",
        },
    }

    assert (
        fake_himp.automation.received_task_id
        == "health_check"
    )

    assert (
        fake_himp.automation.received_confirmed
        is True
    )


def test_run_automation_defaults_confirmation_to_false(
    monkeypatch,
):
    class FakeAutomation:
        def __init__(self):
            self.received_confirmed = None

        def run(self, task_id, confirmed=False):
            self.received_confirmed = confirmed

            return {
                "id": 43,
                "task": task_id,
                "success": True,
                "result": {
                    "success": True,
                },
            }

    class FakeHIMP:
        def __init__(self):
            self.automation = FakeAutomation()

    fake_himp = FakeHIMP()

    monkeypatch.setattr(
        automation,
        "himp",
        fake_himp,
    )

    response = automation.run_automation(
        "health_check"
    )

    import json

    body = json.loads(response.body)

    assert response.status_code == 200
    assert body["id"] == 43
    assert body["task"] == "health_check"
    assert body["success"] is True

    assert (
        fake_himp.automation.received_confirmed
        is False
    )


def test_run_automation_unknown_task_returns_404(
    monkeypatch,
):
    class FakeAutomation:
        def run(self, task_id, confirmed=False):
            raise ValueError(
                f"Automation task not found: {task_id}"
            )

    class FakeHIMP:
        def __init__(self):
            self.automation = FakeAutomation()

    monkeypatch.setattr(
        automation,
        "himp",
        FakeHIMP(),
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        automation.run_automation(
            "missing_task"
        )

    assert captured.value.status_code == 404
    assert (
        captured.value.detail
        == "Automation task not found: missing_task"
    )


@pytest.mark.parametrize(
    "exception",
    [
        automation.AutomationAlreadyRunningError(
            "Automation is already running."
        ),
        automation.AutomationDisabledError(
            "Automation is disabled."
        ),
        automation.AutomationConfirmationRequiredError(
            "Confirmation is required."
        ),
        automation.AutomationDependencyNotSatisfiedError(
            "Automation dependency is not satisfied."
        ),
    ],
)
def test_run_automation_conflict_errors_return_409(
    monkeypatch,
    exception,
):
    class FakeAutomation:
        def run(self, task_id, confirmed=False):
            raise exception

    class FakeHIMP:
        def __init__(self):
            self.automation = FakeAutomation()

    monkeypatch.setattr(
        automation,
        "himp",
        FakeHIMP(),
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        automation.run_automation(
            "health_check"
        )

    assert captured.value.status_code == 409
    assert captured.value.detail == str(exception)


def test_run_automation_unexpected_runtime_error_returns_500(
    monkeypatch,
):
    class FakeAutomation:
        def run(self, task_id, confirmed=False):
            raise RuntimeError(
                "unexpected automation execution failure"
            )

    class FakeHIMP:
        def __init__(self):
            self.automation = FakeAutomation()

    monkeypatch.setattr(
        automation,
        "himp",
        FakeHIMP(),
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        automation.run_automation(
            "health_check"
        )

    assert captured.value.status_code == 500
    assert (
        captured.value.detail
        == "unexpected automation execution failure"
    )


def test_run_automation_timeout_returns_500(
    monkeypatch,
):
    class FakeAutomation:
        def run(self, task_id, confirmed=False):
            raise TimeoutError(
                "Ansible playbook timed out"
            )

    class FakeHIMP:
        def __init__(self):
            self.automation = FakeAutomation()

    monkeypatch.setattr(
        automation,
        "himp",
        FakeHIMP(),
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        automation.run_automation(
            "scheduled_updates"
        )

    assert captured.value.status_code == 500
    assert (
        captured.value.detail
        == "Ansible playbook timed out"
    )
