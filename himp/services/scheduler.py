"""
Scheduler Service.

Provides HIMP automation schedule configuration,
validation, and due-task evaluation.
"""

from datetime import datetime

from himp.database.scheduler import SchedulerRepository


class SchedulerService:
    """
    Provides scheduler configuration and execution
    decision operations.
    """

    FREQUENCIES = {
        "manual",
        "hourly",
        "daily",
        "weekly",
        "monthly",
    }

    def __init__(self):
        self.repository = SchedulerRepository()

    def all(self):
        return self.repository.all()

    def find(
        self,
        task_id,
    ):
        schedule = self.repository.find(
            task_id
        )

        if schedule is None:
            raise ValueError(
                f"Automation task does not exist: {task_id}"
            )

        return schedule

    def update(
        self,
        task_id,
        enabled,
        frequency,
        schedule_time=None,
        day_of_week=None,
    ):
        self.find(task_id)

        self._validate_frequency(
            frequency
        )

        self._validate_time(
            frequency,
            schedule_time,
        )

        self._validate_day(
            frequency,
            day_of_week,
        )

        return self.repository.update(
            task_id=task_id,
            enabled=enabled,
            frequency=frequency,
            schedule_time=schedule_time,
            day_of_week=day_of_week,
        )

    def record_run(
        self,
        task_id,
    ):
        self.find(task_id)

        return self.repository.record_run(
            task_id
        )

    def due(
        self,
        schedule,
        now=None,
    ):
        if not schedule["enabled"]:
            return False

        frequency = schedule["frequency"]

        if frequency == "manual":
            return False

        if now is None:
            now = datetime.now()

        schedule_time = schedule["schedule_time"]

        if schedule_time is None:
            return False

        if frequency == "daily":
            if now.strftime("%H:%M") != schedule_time:
                return False

        elif frequency == "weekly":
            sunday_based_weekday = (
                now.weekday() + 1
            ) % 7

            if (
                sunday_based_weekday
                != schedule["day_of_week"]
            ):
                return False

            if now.strftime("%H:%M") != schedule_time:
                return False

        else:
            return False

        last_run = schedule["last_run"]

        if last_run is None:
            return True

        if isinstance(last_run, str):
            try:
                last_run = datetime.fromisoformat(
                    last_run
                )
            except ValueError:
                return True

        if frequency == "daily":
            return last_run.date() != now.date()

        if frequency == "weekly":
            return (
                last_run.date()
                != now.date()
            )

        return True

    def due_tasks(
        self,
        now=None,
    ):
        if now is None:
            now = datetime.now()

        return [
            schedule
            for schedule in self.all()
            if self.due(
                schedule,
                now,
            )
        ]

    def _validate_frequency(
        self,
        frequency,
    ):
        if frequency not in self.FREQUENCIES:
            raise ValueError(
                "Invalid schedule frequency: "
                f"{frequency}"
            )

    def _validate_time(
        self,
        frequency,
        schedule_time,
    ):
        if frequency == "manual":
            if schedule_time is not None:
                raise ValueError(
                    "Manual schedules cannot specify a time"
                )

            return

        if schedule_time is None:
            raise ValueError(
                f"{frequency.capitalize()} schedules require a time"
            )

        try:
            datetime.strptime(
                schedule_time,
                "%H:%M",
            )
        except ValueError as exc:
            raise ValueError(
                "Schedule time must use HH:MM format"
            ) from exc

    def _validate_day(
        self,
        frequency,
        day_of_week,
    ):
        if frequency != "weekly":
            if day_of_week is not None:
                raise ValueError(
                    "Day of week is only valid for weekly schedules"
                )

            return

        if day_of_week is None:
            raise ValueError(
                "Weekly schedules require a day of week"
            )

        if not isinstance(
            day_of_week,
            int,
        ):
            raise ValueError(
                "Day of week must be an integer from 0 to 6"
            )

        if day_of_week < 0 or day_of_week > 6:
            raise ValueError(
                "Day of week must be an integer from 0 to 6"
            )
