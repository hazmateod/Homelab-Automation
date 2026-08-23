from types import SimpleNamespace

from himp.commands import scheduler_run


class FakeAutomation:
    def run(self, task_id):
        raise AssertionError(
            "automation.run should not be called"
        )


class FakeHIMP:
    automation = FakeAutomation()


class BlockingMaintenanceWindows:
    def __init__(self):
        self.calls = []

    def blocking_window(
        self,
        task_id,
        now=None,
    ):
        self.calls.append(
            {
                "task_id": task_id,
                "now": now,
            }
        )

        return {
            "id": 1,
            "name": "Protected Maintenance",
            "reason": "Scheduled maintenance",
            "task_id": task_id,
            "starts_at": "2026-08-24 01:00:00",
            "ends_at": "2026-08-24 02:00:00",
            "enabled": True,
        }


class NoDueRemediation:
    def due(
        self,
        now=None,
        limit=100,
    ):
        return []


class DueRecurringScheduler:
    def __init__(self):
        self.recorded = []

    def due_tasks(self, now):
        return [
            {
                "task_id": "health_check",
            }
        ]

    def record_run(self, task_id):
        self.recorded.append(
            task_id
        )


class RecordingDispatcher:
    def __init__(
        self,
        automation=None,
    ):
        self.automation = automation
        self.calls = []

    def dispatch(
        self,
        task_id,
    ):
        self.calls.append(
            task_id
        )

        raise AssertionError(
            "dispatch should not be called while blocked"
        )


def test_blocked_recurring_task_is_not_dispatched_or_recorded(
    monkeypatch,
):
    scheduler = DueRecurringScheduler()
    maintenance = BlockingMaintenanceWindows()
    dispatcher_holder = {}

    def make_dispatcher(
        automation=None,
    ):
        dispatcher = RecordingDispatcher(
            automation=automation,
        )

        dispatcher_holder["dispatcher"] = dispatcher

        return dispatcher

    monkeypatch.setattr(
        scheduler_run,
        "HIMP",
        FakeHIMP,
    )

    monkeypatch.setattr(
        scheduler_run,
        "SchedulerService",
        lambda: scheduler,
    )

    monkeypatch.setattr(
        scheduler_run,
        "RemediationSchedulingService",
        NoDueRemediation,
    )

    monkeypatch.setattr(
        scheduler_run,
        "MaintenanceWindowService",
        lambda: maintenance,
    )

    monkeypatch.setattr(
        scheduler_run,
        "OperationalDispatcher",
        make_dispatcher,
    )

    monkeypatch.setattr(
        scheduler_run.PostgreSQLDatabase,
        "close_pools",
        lambda: None,
    )

    result = scheduler_run.run(
        SimpleNamespace(
            at="2026-08-24T01:30:00+00:00"
        )
    )

    assert result == 0

    assert dispatcher_holder[
        "dispatcher"
    ].calls == []

    assert scheduler.recorded == []

    assert maintenance.calls[0][
        "task_id"
    ] == "health_check"


class EmptyScheduler:
    def due_tasks(self, now):
        return []

    def record_run(self, task_id):
        raise AssertionError(
            "record_run should not be called"
        )


class FakeApprovalRepository:
    def find(
        self,
        approval_id,
    ):
        assert approval_id == 7

        return {
            "id": 7,
            "task_id": "scheduled_updates",
        }


class DueBlockedRemediation:
    def __init__(self):
        self.approvals = FakeApprovalRepository()
        self.execute_calls = []

    def due(
        self,
        now=None,
        limit=100,
    ):
        return [
            {
                "id": 9,
                "approval_id": 7,
                "scheduled_for":
                    "2026-08-24 01:30:00",
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

        raise AssertionError(
            "execute_due should not be called while blocked"
        )


class PassiveDispatcher:
    def __init__(
        self,
        automation=None,
    ):
        self.automation = automation


def test_blocked_remediation_is_not_claimed_or_executed(
    monkeypatch,
):
    remediation = DueBlockedRemediation()
    maintenance = BlockingMaintenanceWindows()

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
        "RemediationSchedulingService",
        lambda: remediation,
    )

    monkeypatch.setattr(
        scheduler_run,
        "MaintenanceWindowService",
        lambda: maintenance,
    )

    monkeypatch.setattr(
        scheduler_run,
        "OperationalDispatcher",
        PassiveDispatcher,
    )

    monkeypatch.setattr(
        scheduler_run.PostgreSQLDatabase,
        "close_pools",
        lambda: None,
    )

    result = scheduler_run.run(
        SimpleNamespace(
            at="2026-08-24T01:30:00+00:00"
        )
    )

    assert result == 0

    assert remediation.execute_calls == []

    assert maintenance.calls[0][
        "task_id"
    ] == "scheduled_updates"
