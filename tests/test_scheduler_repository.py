from datetime import datetime

from himp.database.scheduler import SchedulerRepository


def test_seed_reconciles_existing_schedule_without_losing_history():
    repository = SchedulerRepository()

    repository.database.execute(
        """
        UPDATE automation_schedules
        SET frequency=?,
            schedule_time=?,
            day_of_week=?,
            last_run=?
        WHERE task_id=?
        """,
        (
            "weekly",
            "03:15",
            0,
            "2026-08-15 03:15:00",
            "scheduled_updates",
        ),
    )

    before = repository.find("scheduled_updates")

    assert before["frequency"] == "weekly"
    assert before["schedule_time"] == "03:15"
    assert before["day_of_week"] == 0
    assert before["last_run"] is not None

    repository.initialize()

    after = repository.find("scheduled_updates")

    assert after["id"] == before["id"]
    assert after["frequency"] == "daily"
    assert after["schedule_time"] == "03:15"
    assert after["day_of_week"] is None
    assert after["last_run"] == before["last_run"]

def test_health_check_seed_reconciles_daily_schedule_without_losing_history():
    from himp.database.scheduler import SchedulerRepository

    repository = SchedulerRepository()

    repository.database.execute(
        """
        UPDATE automation_schedules
        SET frequency=?,
            schedule_time=?,
            day_of_week=?,
            last_run=?
        WHERE task_id=?
        """,
        (
            "manual",
            None,
            None,
            "2026-08-19 20:20:16",
            "health_check",
        ),
    )

    before = repository.find(
        "health_check"
    )

    assert before["frequency"] == "manual"
    assert before["schedule_time"] is None
    assert before["last_run"] is not None

    repository.initialize()

    after = repository.find(
        "health_check"
    )

    assert after["id"] == before["id"]
    assert after["frequency"] == "daily"
    assert after["schedule_time"] == "04:00"
    assert after["day_of_week"] is None
    assert after["last_run"] == before["last_run"]


def test_health_check_seed_has_daily_0400_schedule():
    from himp.database.scheduler import SchedulerRepository

    repository = SchedulerRepository()

    schedule = repository.find(
        "health_check"
    )

    assert schedule["enabled"] == 1
    assert schedule["frequency"] == "daily"
    assert schedule["schedule_time"] == "04:00"
    assert schedule["day_of_week"] is None
