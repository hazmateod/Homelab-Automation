import pytest

from fastapi import HTTPException

from himp.api import scheduler


class FakeSchedulerService:
    def all(self):
        return [
            {
                "task_id": "health_check",
                "enabled": True,
                "frequency": "daily",
                "schedule_time": "02:00",
                "day_of_week": None,
                "day_of_month": None,
                "last_run": None,
            },
            {
                "task_id": "generate_reports",
                "enabled": False,
                "frequency": "manual",
                "schedule_time": None,
                "day_of_week": None,
                "day_of_month": None,
                "last_run": None,
            },
        ]


def test_scheduler_summary_returns_schedules(
    monkeypatch,
):
    monkeypatch.setattr(
        scheduler,
        "service",
        FakeSchedulerService(),
    )

    import asyncio

    response = asyncio.run(
        scheduler.scheduler_summary()
    )

    assert response["count"] == 2
    assert len(response["schedules"]) == 2

    assert response["schedules"][0] == {
        "task_id": "health_check",
        "enabled": True,
        "frequency": "daily",
        "schedule_time": "02:00",
        "day_of_week": None,
        "day_of_month": None,
        "last_run": None,
    }

    assert response["schedules"][1] == {
        "task_id": "generate_reports",
        "enabled": False,
        "frequency": "manual",
        "schedule_time": None,
        "day_of_week": None,
        "day_of_month": None,
        "last_run": None,
    }


def test_scheduler_detail_returns_schedule_and_next_run(
    monkeypatch,
):
    class FakeSchedulerService:
        def find(self, task_id):
            assert task_id == "health_check"

            return {
                "task_id": "health_check",
                "enabled": True,
                "frequency": "daily",
                "schedule_time": "02:00",
                "day_of_week": None,
                "day_of_month": None,
                "last_run": None,
            }

        def next_run(self, schedule):
            assert schedule["task_id"] == "health_check"

            from datetime import datetime, timezone

            return datetime(
                2026,
                8,
                12,
                2,
                0,
                tzinfo=timezone.utc,
            )

    monkeypatch.setattr(
        scheduler,
        "service",
        FakeSchedulerService(),
    )

    import asyncio

    response = asyncio.run(
        scheduler.scheduler_task(
            "health_check"
        )
    )

    assert response == {
        "task_id": "health_check",
        "enabled": True,
        "frequency": "daily",
        "schedule_time": "02:00",
        "day_of_week": None,
        "day_of_month": None,
        "last_run": None,
        "next_run": "2026-08-12T02:00:00+00:00",
    }


def test_scheduler_task_missing_returns_404(
    monkeypatch,
):
    class FakeSchedulerService:
        def find(self, task_id):
            raise ValueError(
                f"Unknown scheduler task: {task_id}"
            )

    monkeypatch.setattr(
        scheduler,
        "service",
        FakeSchedulerService(),
    )

    import asyncio

    with pytest.raises(
        HTTPException
    ) as captured:
        asyncio.run(
            scheduler.scheduler_task(
                "missing_task"
            )
        )

    assert captured.value.status_code == 404
    assert captured.value.detail == {
        "error": "Unknown scheduler task: missing_task",
        "task_id": "missing_task",
    }


def test_scheduler_task_status_returns_never_run_status(
    monkeypatch,
):
    class FakeSchedulerService:
        def execution_status(self, task_id):
            assert task_id == "health_check"

            return {
                "task_id": "health_check",
                "schedule": {
                    "task_id": "health_check",
                    "enabled": True,
                    "frequency": "daily",
                    "schedule_time": "02:00",
                    "day_of_week": None,
                    "day_of_month": None,
                    "last_run": None,
                },
                "next_run": "2026-08-12T02:00:00+00:00",
                "last_execution": None,
                "last_execution_success": None,
                "last_execution_at": None,
                "last_execution_elapsed": None,
                "last_execution_error": None,
            }

    monkeypatch.setattr(
        scheduler,
        "service",
        FakeSchedulerService(),
    )

    import asyncio

    response = asyncio.run(
        scheduler.scheduler_task_status(
            "health_check"
        )
    )

    assert response == {
        "task_id": "health_check",
        "schedule": {
            "task_id": "health_check",
            "enabled": True,
            "frequency": "daily",
            "schedule_time": "02:00",
            "day_of_week": None,
            "day_of_month": None,
            "last_run": None,
        },
        "next_run": "2026-08-12T02:00:00+00:00",
        "last_execution": None,
        "last_execution_success": None,
        "last_execution_at": None,
        "last_execution_elapsed": None,
        "last_execution_error": None,
    }


def test_scheduler_task_status_returns_last_execution(
    monkeypatch,
):
    class FakeSchedulerService:
        def execution_status(self, task_id):
            assert task_id == "health_check"

            return {
                "task_id": "health_check",
                "schedule": {
                    "task_id": "health_check",
                    "enabled": True,
                    "frequency": "daily",
                    "schedule_time": "02:00",
                    "day_of_week": None,
                    "day_of_month": None,
                    "last_run": "2026-08-11T02:00:00+00:00",
                },
                "next_run": "2026-08-12T02:00:00+00:00",
                "last_execution": {
                    "id": 42,
                    "task_id": "health_check",
                    "success": True,
                    "elapsed": 1.25,
                    "result": {
                        "success": True,
                        "message": "healthy",
                    },
                },
                "last_execution_success": True,
                "last_execution_at": "2026-08-11T02:00:00+00:00",
                "last_execution_elapsed": 1.25,
                "last_execution_error": None,
            }

    monkeypatch.setattr(
        scheduler,
        "service",
        FakeSchedulerService(),
    )

    import asyncio

    response = asyncio.run(
        scheduler.scheduler_task_status(
            "health_check"
        )
    )

    assert response["task_id"] == "health_check"
    assert response["next_run"] == (
        "2026-08-12T02:00:00+00:00"
    )
    assert response["last_execution"] == {
        "id": 42,
        "task_id": "health_check",
        "success": True,
        "elapsed": 1.25,
        "result": {
            "success": True,
            "message": "healthy",
        },
    }
    assert response["last_execution_success"] is True
    assert response["last_execution_at"] == (
        "2026-08-11T02:00:00+00:00"
    )
    assert response["last_execution_elapsed"] == 1.25
    assert response["last_execution_error"] is None


def test_scheduler_task_status_missing_returns_404(
    monkeypatch,
):
    class FakeSchedulerService:
        def execution_status(self, task_id):
            raise ValueError(
                f"Unknown scheduler task: {task_id}"
            )

    monkeypatch.setattr(
        scheduler,
        "service",
        FakeSchedulerService(),
    )

    import asyncio

    with pytest.raises(
        HTTPException
    ) as captured:
        asyncio.run(
            scheduler.scheduler_task_status(
                "missing_task"
            )
        )

    assert captured.value.status_code == 404
    assert captured.value.detail == {
        "error": "Unknown scheduler task: missing_task",
        "task_id": "missing_task",
    }


def test_update_scheduler_task_returns_updated_schedule(
    monkeypatch,
):
    class FakeSchedulerService:
        def update(
            self,
            task_id,
            enabled,
            frequency,
            schedule_time=None,
            day_of_week=None,
            day_of_month=None,
        ):
            assert task_id == "health_check"
            assert enabled is True
            assert frequency == "weekly"
            assert schedule_time == "03:30"
            assert day_of_week == 2
            assert day_of_month is None

            return {
                "task_id": "health_check",
                "enabled": True,
                "frequency": "weekly",
                "schedule_time": "03:30",
                "day_of_week": 2,
                "day_of_month": None,
            }

    monkeypatch.setattr(
        scheduler,
        "service",
        FakeSchedulerService(),
    )

    request = scheduler.SchedulerUpdate(
        enabled=True,
        frequency="weekly",
        schedule_time="03:30",
        day_of_week=2,
        day_of_month=None,
    )

    import asyncio

    response = asyncio.run(
        scheduler.update_scheduler_task(
            "health_check",
            request,
        )
    )

    assert response == {
        "schedule": {
            "task_id": "health_check",
            "enabled": True,
            "frequency": "weekly",
            "schedule_time": "03:30",
            "day_of_week": 2,
            "day_of_month": None,
        },
        "message": (
            "Automation schedule updated successfully."
        ),
    }


def test_update_scheduler_task_missing_returns_404(
    monkeypatch,
):
    class FakeSchedulerService:
        def update(
            self,
            task_id,
            enabled,
            frequency,
            schedule_time=None,
            day_of_week=None,
            day_of_month=None,
        ):
            raise ValueError(
                "Automation task does not exist: "
                f"{task_id}"
            )

    monkeypatch.setattr(
        scheduler,
        "service",
        FakeSchedulerService(),
    )

    request = scheduler.SchedulerUpdate(
        enabled=True,
        frequency="daily",
        schedule_time="02:00",
    )

    import asyncio

    with pytest.raises(
        HTTPException
    ) as captured:
        asyncio.run(
            scheduler.update_scheduler_task(
                "missing_task",
                request,
            )
        )

    assert captured.value.status_code == 404
    assert captured.value.detail == {
        "error": (
            "Automation task does not exist: "
            "missing_task"
        ),
        "task_id": "missing_task",
    }


def test_update_scheduler_task_invalid_schedule_returns_400(
    monkeypatch,
):
    class FakeSchedulerService:
        def update(
            self,
            task_id,
            enabled,
            frequency,
            schedule_time=None,
            day_of_week=None,
            day_of_month=None,
        ):
            raise ValueError(
                "Unsupported scheduler frequency: hourly"
            )

    monkeypatch.setattr(
        scheduler,
        "service",
        FakeSchedulerService(),
    )

    request = scheduler.SchedulerUpdate(
        enabled=True,
        frequency="hourly",
        schedule_time="02:00",
    )

    import asyncio

    with pytest.raises(
        HTTPException
    ) as captured:
        asyncio.run(
            scheduler.update_scheduler_task(
                "health_check",
                request,
            )
        )

    assert captured.value.status_code == 400
    assert captured.value.detail == {
        "error": (
            "Unsupported scheduler frequency: hourly"
        ),
        "task_id": "health_check",
    }


def test_record_scheduler_run_returns_updated_schedule(
    monkeypatch,
):
    class FakeSchedulerService:
        def record_run(self, task_id):
            assert task_id == "health_check"

            return {
                "task_id": "health_check",
                "enabled": True,
                "frequency": "daily",
                "schedule_time": "02:00",
                "day_of_week": None,
                "day_of_month": None,
                "last_run": "2026-08-11T21:00:00+00:00",
            }

    monkeypatch.setattr(
        scheduler,
        "service",
        FakeSchedulerService(),
    )

    import asyncio

    response = asyncio.run(
        scheduler.record_scheduler_run(
            "health_check"
        )
    )

    assert response == {
        "schedule": {
            "task_id": "health_check",
            "enabled": True,
            "frequency": "daily",
            "schedule_time": "02:00",
            "day_of_week": None,
            "day_of_month": None,
            "last_run": "2026-08-11T21:00:00+00:00",
        },
        "message": (
            "Automation run recorded successfully."
        ),
    }


def test_record_scheduler_run_missing_returns_404(
    monkeypatch,
):
    class FakeSchedulerService:
        def record_run(self, task_id):
            raise ValueError(
                f"Automation task does not exist: {task_id}"
            )

    monkeypatch.setattr(
        scheduler,
        "service",
        FakeSchedulerService(),
    )

    import asyncio

    with pytest.raises(
        HTTPException
    ) as captured:
        asyncio.run(
            scheduler.record_scheduler_run(
                "missing_task"
            )
        )

    assert captured.value.status_code == 404
    assert captured.value.detail == {
        "error": (
            "Automation task does not exist: "
            "missing_task"
        ),
        "task_id": "missing_task",
    }
