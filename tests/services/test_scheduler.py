from datetime import datetime

from himp.services.scheduler import SchedulerService


def make_service():
    service = object.__new__(SchedulerService)
    return service


def make_daily_schedule(last_run=None):
    return {
        "task_id": "health_check",
        "enabled": True,
        "frequency": "daily",
        "schedule_time": "02:00",
        "day_of_week": None,
        "day_of_month": None,
        "last_run": last_run,
    }


def test_daily_schedule_is_due_when_never_run():
    service = make_service()

    schedule = make_daily_schedule()

    assert service.due(
        schedule,
        datetime(2026, 8, 12, 2, 30),
    ) is True


def test_daily_schedule_is_not_due_twice_for_same_occurrence():
    service = make_service()

    schedule = make_daily_schedule(
        last_run="2026-08-12T02:05:00-04:00",
    )

    assert service.due(
        schedule,
        datetime(2026, 8, 12, 2, 30),
    ) is False


def test_daily_schedule_detects_missed_occurrence_once():
    service = make_service()

    schedule = make_daily_schedule(
        last_run="2026-08-11T02:05:00",
    )

    now = datetime(
        2026,
        8,
        12,
        8,
        30,
    )

    assert service.due(
        schedule,
        now,
    ) is True

    schedule["last_run"] = now.isoformat()

    assert service.due(
        schedule,
        now,
    ) is False


def test_daily_schedule_becomes_due_for_next_occurrence():
    service = make_service()

    schedule = make_daily_schedule(
        last_run="2026-08-12T02:05:00",
    )

    assert service.due(
        schedule,
        datetime(2026, 8, 13, 2, 30),
    ) is True


def test_daily_schedule_before_scheduled_time_is_not_due():
    service = make_service()

    schedule = make_daily_schedule()

    assert service.due(
        schedule,
        datetime(2026, 8, 12, 1, 59),
    ) is False


def test_timezone_aware_last_run_prevents_duplicate_occurrence():
    service = make_service()

    schedule = make_daily_schedule(
        last_run="2026-08-12T02:05:00-04:00",
    )

    assert service.due(
        schedule,
        datetime(2026, 8, 12, 2, 30),
    ) is False


def test_successful_execution_without_record_run_leaves_occurrence_due():
    service = make_service()

    schedule = make_daily_schedule(
        last_run="2026-08-11T02:05:00-04:00",
    )

    evaluation_time = datetime(
        2026,
        8,
        12,
        2,
        30,
    )

    assert service.due(
        schedule,
        evaluation_time,
    ) is True


def test_execution_status_exposes_ansible_success_diagnostics():
    service = make_service()

    service.find = lambda task_id: make_daily_schedule()
    service.next_run = lambda schedule: None

    service.execution_repository = type(
        "FakeExecutionRepository",
        (),
        {
            "latest": lambda self, task_id: {
                "id": 101,
                "task_id": task_id,
                "success": True,
                "elapsed": 12.5,
                "executed_at": "2026-08-15T03:00:12+00:00",
                "result": {
                    "task": task_id,
                    "attempt": 1,
                    "attempts": 1,
                    "result": {
                        "target": "maintenance",
                        "success": True,
                        "return_code": 0,
                        "elapsed": 12.5,
                        "stdout": "PLAY RECAP\nok=5",
                        "stderr": "",
                    },
                },
            },
        },
    )()

    result = service.execution_status("health_check")

    assert result["last_execution_success"] is True
    assert result["last_execution_return_code"] == 0
    assert result["last_execution_error"] is None


def test_execution_status_exposes_ansible_failure_diagnostics():
    service = make_service()

    service.find = lambda task_id: make_daily_schedule()
    service.next_run = lambda schedule: None

    service.execution_repository = type(
        "FakeExecutionRepository",
        (),
        {
            "latest": lambda self, task_id: {
                "id": 102,
                "task_id": task_id,
                "success": False,
                "elapsed": 8.25,
                "executed_at": "2026-08-15T03:01:12+00:00",
                "result": {
                    "task": task_id,
                    "attempt": 1,
                    "attempts": 1,
                    "result": {
                        "target": "maintenance",
                        "success": False,
                        "return_code": 2,
                        "elapsed": 8.25,
                        "stdout": "PLAY RECAP\nfailed=1",
                        "stderr": "fatal: [pve01]: FAILED!",
                    },
                },
            },
        },
    )()

    result = service.execution_status("health_check")

    assert result["last_execution_success"] is False
    assert result["last_execution_return_code"] == 2
    assert result["last_execution_error"] == (
        "fatal: [pve01]: FAILED!"
    )


def test_execution_status_preserves_exception_error():
    service = make_service()

    service.find = lambda task_id: make_daily_schedule()
    service.next_run = lambda schedule: None

    service.execution_repository = type(
        "FakeExecutionRepository",
        (),
        {
            "latest": lambda self, task_id: {
                "id": 103,
                "task_id": task_id,
                "success": False,
                "elapsed": 0.5,
                "executed_at": "2026-08-15T03:02:12+00:00",
                "result": {
                    "task": task_id,
                    "attempt": 1,
                    "attempts": 1,
                    "result": {
                        "success": False,
                        "error": "Automation failed.",
                    },
                },
            },
        },
    )()

    result = service.execution_status("health_check")

    assert result["last_execution_success"] is False
    assert result["last_execution_return_code"] is None
    assert result["last_execution_error"] == (
        "Automation failed."
    )
