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
