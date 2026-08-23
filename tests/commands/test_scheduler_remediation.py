from types import SimpleNamespace

from himp.commands import scheduler_run


class EmptyAutomation:
    def run(self, task_id):
        raise AssertionError(
            "Recurring automation should not execute"
        )


class FakeHIMP:
    automation = EmptyAutomation()


class EmptyScheduler:
    def due_tasks(self, now):
        return []

    def record_run(self, task_id):
        raise AssertionError(
            "No recurring schedule should be recorded"
        )


class NoMaintenanceWindows:
    def blocking_window(
        self,
        task_id,
        now=None,
    ):
        return None


class FakeApprovalRepository:
    def find(
        self,
        approval_id,
    ):
        if approval_id == 7:
            return {
                "id": 7,
                "task_id": "scheduled_updates",
            }

        return None


class DueRemediationScheduling:
    def __init__(
        self,
        result_status="COMPLETED",
    ):
        self.result_status = result_status
        self.due_calls = []
        self.execute_calls = []
        self.approvals = FakeApprovalRepository()

    def due(
        self,
        now=None,
        limit=100,
    ):
        self.due_calls.append(
            now
        )

        return [
            {
                "id": 9,
                "approval_id": 7,
                "scheduled_for":
                    "2026-08-21 17:00:00",
                "status": "SCHEDULED",
            }
        ]

    def execute_due(
        self,
        schedule_id,
        now=None,
    ):
        self.execute_calls.append(
            {
                "schedule_id": schedule_id,
                "now": now,
            }
        )

        result = {
            "id": schedule_id,
            "status": self.result_status,
            "audit_id": 55,
            "error": None,
        }

        if self.result_status == "FAILED":
            result["error"] = (
                "policy did not allow execution"
            )

        return result


def test_scheduler_executes_remediation_when_no_recurring_tasks_due(
    monkeypatch,
):
    remediation = (
        DueRemediationScheduling()
    )

    monkeypatch.setattr(
        scheduler_run,
        "HIMP",
        FakeHIMP,
    )

    monkeypatch.setattr(
        scheduler_run,
        "SchedulerService",
        EmptyScheduler,
    )

    monkeypatch.setattr(
        scheduler_run,
        "MaintenanceWindowService",
        NoMaintenanceWindows,
    )

    monkeypatch.setattr(
        scheduler_run,
        "RemediationSchedulingService",
        lambda: remediation,
    )

    monkeypatch.setattr(
        scheduler_run.PostgreSQLDatabase,
        "close_pools",
        lambda: None,
    )

    args = SimpleNamespace(
        at="2026-08-21T13:00:00-04:00"
    )

    result = scheduler_run.run(
        args
    )

    assert result == 0

    assert remediation.execute_calls[0][
        "schedule_id"
    ] == 9

    assert remediation.execute_calls[0][
        "now"
    ].isoformat() == (
        "2026-08-21T17:00:00"
    )


def test_failed_remediation_causes_scheduler_failure(
    monkeypatch,
):
    remediation = (
        DueRemediationScheduling(
            result_status="FAILED"
        )
    )

    monkeypatch.setattr(
        scheduler_run,
        "HIMP",
        FakeHIMP,
    )

    monkeypatch.setattr(
        scheduler_run,
        "SchedulerService",
        EmptyScheduler,
    )

    monkeypatch.setattr(
        scheduler_run,
        "MaintenanceWindowService",
        NoMaintenanceWindows,
    )

    monkeypatch.setattr(
        scheduler_run,
        "RemediationSchedulingService",
        lambda: remediation,
    )

    monkeypatch.setattr(
        scheduler_run.PostgreSQLDatabase,
        "close_pools",
        lambda: None,
    )

    result = scheduler_run.run(
        SimpleNamespace(
            at="2026-08-21T13:00:00-04:00"
        )
    )

    assert result == 1


def test_scheduler_with_no_work_returns_zero(
    monkeypatch,
):
    class EmptyRemediation:
        def due(
            self,
            now=None,
            limit=100,
        ):
            return []

    monkeypatch.setattr(
        scheduler_run,
        "HIMP",
        FakeHIMP,
    )

    monkeypatch.setattr(
        scheduler_run,
        "SchedulerService",
        EmptyScheduler,
    )

    monkeypatch.setattr(
        scheduler_run,
        "MaintenanceWindowService",
        NoMaintenanceWindows,
    )

    monkeypatch.setattr(
        scheduler_run,
        "RemediationSchedulingService",
        EmptyRemediation,
    )

    monkeypatch.setattr(
        scheduler_run.PostgreSQLDatabase,
        "close_pools",
        lambda: None,
    )

    result = scheduler_run.run(
        SimpleNamespace(
            at="2026-08-21T13:00:00-04:00"
        )
    )

    assert result == 0
