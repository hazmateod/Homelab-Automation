import pytest
from himp.commands import scheduler_run
from types import SimpleNamespace


class FakeAutomation:
    def __init__(self):
        self.calls = []

    def run(self, task_id):
        self.calls.append(task_id)

        return {
            "task": task_id,
            "executed_at": "2026-08-11T03:00:00",
            "result": {
                "success": True,
            },
        }


class FakeHIMP:
    def __init__(self, automation):
        self.automation = automation


class FakeScheduler:
    def __init__(self):
        self.recorded = []

    def due_tasks(self, now):
        return [
            {
                "task_id": "health_check",
            },
        ]

    def record_run(self, task_id):
        self.recorded.append(task_id)


class Args:
    at = None


class EmptyRemediationScheduling:
    def due(
        self,
        now=None,
        limit=100,
    ):
        return []

    def execute_due(
        self,
        schedule_id,
        now=None,
    ):
        raise AssertionError(
            "No remediation schedule should execute"
        )


@pytest.fixture(autouse=True)
def empty_remediation_queue(monkeypatch):
    monkeypatch.setattr(
        scheduler_run,
        "RemediationSchedulingService",
        EmptyRemediationScheduling,
    )




def test_scheduler_run_executes_due_task_and_records_run(
    monkeypatch,
):
    automation = FakeAutomation()
    himp = FakeHIMP(automation)
    scheduler = FakeScheduler()

    monkeypatch.setattr(
        scheduler_run,
        "HIMP",
        lambda: himp,
    )

    monkeypatch.setattr(
        scheduler_run,
        "SchedulerService",
        lambda: scheduler,
    )

    result = scheduler_run.run(
        Args()
    )

    assert result == 0
    assert automation.calls == [
        "health_check",
    ]
    assert scheduler.recorded == [
        "health_check",
    ]


def test_scheduler_run_does_not_record_failed_result(
    monkeypatch,
):
    class FakeAutomation:
        def __init__(self):
            self.calls = []

        def run(self, task_id):
            self.calls.append(task_id)

            return {
                "task": task_id,
                "executed_at": "2026-08-11T03:00:00",
                "result": {
                    "success": False,
                    "error": "temporary failure",
                    "error_category": "execution",
                    "retryable": True,
                },
            }

    class FakeHIMP:
        def __init__(self):
            self.automation = FakeAutomation()

    class FakeScheduler:
        def __init__(self):
            self.recorded = []

        def due_tasks(self, now):
            return [
                {
                    "task_id": "health_check",
                },
            ]

        def record_run(self, task_id):
            self.recorded.append(task_id)

    class Args:
        at = None

    himp = FakeHIMP()
    scheduler = FakeScheduler()

    monkeypatch.setattr(
        scheduler_run,
        "HIMP",
        lambda: himp,
    )

    monkeypatch.setattr(
        scheduler_run,
        "SchedulerService",
        lambda: scheduler,
    )

    result = scheduler_run.run(
        Args()
    )

    assert result == 1
    assert himp.automation.calls == [
        "health_check",
    ]
    assert scheduler.recorded == []


def test_scheduler_run_handles_automation_exception(
    monkeypatch,
):
    class FakeAutomation:
        def __init__(self):
            self.calls = []

        def run(self, task_id):
            self.calls.append(task_id)

            raise RuntimeError(
                "automation execution failed"
            )

    class FakeHIMP:
        def __init__(self):
            self.automation = FakeAutomation()

    class FakeScheduler:
        def __init__(self):
            self.recorded = []

        def due_tasks(self, now):
            return [
                {
                    "task_id": "health_check",
                },
            ]

        def record_run(self, task_id):
            self.recorded.append(task_id)

    class Args:
        at = None

    himp = FakeHIMP()
    scheduler = FakeScheduler()

    monkeypatch.setattr(
        scheduler_run,
        "HIMP",
        lambda: himp,
    )

    monkeypatch.setattr(
        scheduler_run,
        "SchedulerService",
        lambda: scheduler,
    )

    result = scheduler_run.run(
        Args()
    )

    assert result == 1
    assert himp.automation.calls == [
        "health_check",
    ]
    assert scheduler.recorded == []


def test_scheduler_run_continues_after_failed_task(
    monkeypatch,
):
    class FakeAutomation:
        def __init__(self):
            self.calls = []

        def run(self, task_id):
            self.calls.append(task_id)

            if task_id == "health_check":
                return {
                    "task": task_id,
                    "executed_at": "2026-08-11T03:00:00",
                    "result": {
                        "success": False,
                        "error": "health failure",
                    },
                }

            return {
                "task": task_id,
                "executed_at": "2026-08-11T03:01:00",
                "result": {
                    "success": True,
                },
            }

    class FakeHIMP:
        def __init__(self):
            self.automation = FakeAutomation()

    class FakeScheduler:
        def __init__(self):
            self.recorded = []

        def due_tasks(self, now):
            return [
                {"task_id": "health_check"},
                {"task_id": "inventory_refresh"},
            ]

        def record_run(self, task_id):
            self.recorded.append(task_id)

    class Args:
        at = None

    himp = FakeHIMP()
    scheduler = FakeScheduler()

    monkeypatch.setattr(
        scheduler_run,
        "HIMP",
        lambda: himp,
    )

    monkeypatch.setattr(
        scheduler_run,
        "SchedulerService",
        lambda: scheduler,
    )

    result = scheduler_run.run(
        Args()
    )

    assert result == 1
    assert himp.automation.calls == [
        "health_check",
        "inventory_refresh",
    ]
    assert scheduler.recorded == [
        "inventory_refresh",
    ]


def test_scheduler_run_returns_zero_when_no_tasks_are_due(
    monkeypatch,
):
    class FakeAutomation:
        def __init__(self):
            self.calls = []

        def run(self, task_id):
            self.calls.append(task_id)

    class FakeHIMP:
        def __init__(self):
            self.automation = FakeAutomation()

    class FakeScheduler:
        def __init__(self):
            self.due_calls = []
            self.recorded = []

        def due_tasks(self, now):
            self.due_calls.append(now)
            return []

        def record_run(self, task_id):
            self.recorded.append(task_id)

    class Args:
        at = None

    himp = FakeHIMP()
    scheduler = FakeScheduler()

    monkeypatch.setattr(
        scheduler_run,
        "HIMP",
        lambda: himp,
    )

    monkeypatch.setattr(
        scheduler_run,
        "SchedulerService",
        lambda: scheduler,
    )

    result = scheduler_run.run(
        Args()
    )

    assert result == 0
    assert himp.automation.calls == []
    assert scheduler.recorded == []
    assert len(scheduler.due_calls) == 1


def test_scheduler_run_invalid_at_returns_two(
    monkeypatch,
    capsys,
):
    class FakeHIMP:
        def __init__(self):
            self.automation = None

    class FakeScheduler:
        def due_tasks(self, now):
            raise AssertionError(
                "due_tasks should not be called"
            )

    class Args:
        at = "not-a-datetime"

    monkeypatch.setattr(
        scheduler_run,
        "HIMP",
        FakeHIMP,
    )

    monkeypatch.setattr(
        scheduler_run,
        "SchedulerService",
        FakeScheduler,
    )

    result = scheduler_run.run(
        Args()
    )

    assert result == 2

    output = capsys.readouterr()

    assert "Invalid --at value." in output.err


def test_scheduler_run_passes_explicit_at_to_scheduler(
    monkeypatch,
):
    from datetime import datetime

    class FakeAutomation:
        def run(self, task_id):
            return {
                "task": task_id,
                "executed_at": "2026-08-11T03:00:00",
                "result": {
                    "success": True,
                },
            }

    class FakeHIMP:
        def __init__(self):
            self.automation = FakeAutomation()

    class FakeScheduler:
        def __init__(self):
            self.received_now = None
            self.recorded = []

        def due_tasks(self, now):
            self.received_now = now

            return [
                {
                    "task_id": "health_check",
                },
            ]

        def record_run(self, task_id):
            self.recorded.append(task_id)

    class Args:
        at = "2026-08-11T03:00:00"

    himp = FakeHIMP()
    scheduler = FakeScheduler()

    monkeypatch.setattr(
        scheduler_run,
        "HIMP",
        lambda: himp,
    )

    monkeypatch.setattr(
        scheduler_run,
        "SchedulerService",
        lambda: scheduler,
    )

    result = scheduler_run.run(
        Args()
    )

    assert result == 0
    assert scheduler.received_now == datetime(
        2026,
        8,
        11,
        3,
        0,
    )
    assert scheduler.recorded == [
        "health_check",
    ]


def test_scheduler_run_reports_failure_when_record_run_fails(
    monkeypatch,
):
    class FakeAutomation:
        def __init__(self):
            self.calls = []

        def run(self, task_id):
            self.calls.append(task_id)

            return {
                "task": task_id,
                "executed_at": "2026-08-11T03:00:00",
                "result": {
                    "success": True,
                },
            }

    class FakeHIMP:
        def __init__(self):
            self.automation = FakeAutomation()

    class FakeScheduler:
        def due_tasks(self, now):
            return [
                {
                    "task_id": "health_check",
                },
            ]

        def record_run(self, task_id):
            raise RuntimeError(
                "scheduler acknowledgement failed"
            )

    class Args:
        at = None

    himp = FakeHIMP()
    scheduler = FakeScheduler()

    monkeypatch.setattr(
        scheduler_run,
        "HIMP",
        lambda: himp,
    )

    monkeypatch.setattr(
        scheduler_run,
        "SchedulerService",
        lambda: scheduler,
    )

    result = scheduler_run.run(
        Args()
    )

    assert result == 1
    assert himp.automation.calls == [
        "health_check",
    ]


def test_scheduler_run_dispatches_remediation_operation(
    monkeypatch,
):
    class FakeAutomation:
        def __init__(self):
            self.calls = []

        def run(self, task_id):
            self.calls.append(task_id)

            return {
                "task": task_id,
                "executed_at": "2026-08-11T03:00:00",
                "result": {
                    "success": True,
                },
            }

    class FakeHIMP:
        def __init__(self):
            self.automation = FakeAutomation()

    class FakeScheduler:
        def __init__(self):
            self.recorded = []

        def due_tasks(self, now):
            return [
                {
                    "task_id": "remediation_operations",
                },
            ]

        def record_run(self, task_id):
            self.recorded.append(task_id)

    class FakeDispatcher:
        def __init__(self, automation):
            self.automation = automation
            self.calls = []

        def dispatch(self, task_id):
            self.calls.append(task_id)

            return {
                "task": task_id,
                "executed_at": "2026-08-11T03:00:00",
                "success": True,
                "result": {
                    "success": True,
                    "source_type": "host",
                    "source_id": "pve01",
                    "confirmed": False,
                },
            }

    class Args:
        at = None

    himp = FakeHIMP()
    scheduler = FakeScheduler()

    dispatcher_holder = {}

    def make_dispatcher(automation):
        dispatcher = FakeDispatcher(
            automation
        )
        dispatcher_holder["dispatcher"] = dispatcher
        return dispatcher

    monkeypatch.setattr(
        scheduler_run,
        "HIMP",
        lambda: himp,
    )

    monkeypatch.setattr(
        scheduler_run,
        "SchedulerService",
        lambda: scheduler,
    )

    monkeypatch.setattr(
        scheduler_run,
        "OperationalDispatcher",
        make_dispatcher,
    )

    result = scheduler_run.run(
        Args()
    )

    assert result == 0
    assert dispatcher_holder["dispatcher"].calls == [
        "remediation_operations",
    ]
    assert himp.automation.calls == []
    assert scheduler.recorded == [
        "remediation_operations",
    ]


def test_scheduler_run_does_not_auto_confirm_remediation(
    monkeypatch,
):
    class FakeHIMP:
        def __init__(self):
            self.automation = object()

    class FakeScheduler:
        def due_tasks(self, now):
            return [
                {
                    "task_id": "remediation_operations",
                },
            ]

        def record_run(self, task_id):
            pass

    class FakeDispatcher:
        def __init__(self, automation):
            self.calls = []

        def dispatch(self, task_id):
            self.calls.append(task_id)

            return {
                "task": task_id,
                "executed_at": "2026-08-11T03:00:00",
                "success": True,
                "result": {
                    "success": True,
                    "confirmation_required": True,
                    "decision": "CONFIRM_REQUIRED",
                    "confirmed": False,
                },
            }

    class Args:
        at = None

    dispatcher_holder = {}

    def make_dispatcher(automation):
        dispatcher = FakeDispatcher(
            automation
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
        FakeScheduler,
    )

    monkeypatch.setattr(
        scheduler_run,
        "OperationalDispatcher",
        make_dispatcher,
    )

    result = scheduler_run.run(
        Args()
    )

    assert result == 0
    assert dispatcher_holder["dispatcher"].calls == [
        "remediation_operations",
    ]


def test_scheduler_run_records_disabled_remediation(
    monkeypatch,
):
    class FakeHIMP:
        def __init__(self):
            self.automation = object()

    class FakeScheduler:
        def __init__(self):
            self.recorded = []

        def due_tasks(self, now):
            return [
                {
                    "task_id": "remediation_operations",
                },
            ]

        def record_run(self, task_id):
            self.recorded.append(task_id)

    class FakeDispatcher:
        def __init__(self, automation):
            pass

        def dispatch(self, task_id):
            return {
                "task": task_id,
                "executed_at": "2026-08-11T03:00:00",
                "success": True,
                "skipped": True,
                "result": {
                    "success": True,
                    "skipped": True,
                },
            }

    class Args:
        at = None

    scheduler = FakeScheduler()

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
        "OperationalDispatcher",
        FakeDispatcher,
    )

    result = scheduler_run.run(
        Args()
    )

    assert result == 0
    assert scheduler.recorded == [
        "remediation_operations",
    ]


def test_scheduler_run_fails_closed_for_missing_remediation_configuration(
    monkeypatch,
):
    class FakeHIMP:
        def __init__(self):
            self.automation = object()

    class FakeScheduler:
        def __init__(self):
            self.recorded = []

        def due_tasks(self, now):
            return [
                {
                    "task_id": "remediation_operations",
                },
            ]

        def record_run(self, task_id):
            self.recorded.append(task_id)

    class FakeDispatcher:
        def __init__(self, automation):
            pass

        def dispatch(self, task_id):
            return {
                "task": task_id,
                "executed_at": "2026-08-11T03:00:00",
                "success": False,
                "error_category": "configuration",
                "result": {
                    "success": False,
                    "error": (
                        "Remediation operational "
                        "configuration is not configured."
                    ),
                },
            }

    class Args:
        at = None

    scheduler = FakeScheduler()

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
        "OperationalDispatcher",
        FakeDispatcher,
    )

    result = scheduler_run.run(
        Args()
    )

    assert result == 1
    assert scheduler.recorded == []


def test_scheduler_run_closes_postgresql_pools(monkeypatch):
    calls = []

    automation = FakeAutomation()
    himp = FakeHIMP(automation)
    scheduler = FakeScheduler()

    class FakePoolDatabase:
        @classmethod
        def close_pools(cls):
            calls.append("close_pools")

    monkeypatch.setattr(
        scheduler_run,
        "PostgreSQLDatabase",
        FakePoolDatabase,
    )
    monkeypatch.setattr(
        scheduler_run,
        "HIMP",
        lambda: himp,
    )
    monkeypatch.setattr(
        scheduler_run,
        "SchedulerService",
        lambda: scheduler,
    )

    result = scheduler_run.run(
        Args()
    )

    assert result == 0
    assert calls == ["close_pools"]
