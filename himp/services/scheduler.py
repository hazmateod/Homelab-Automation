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
        day_of_month=None,
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

        self._validate_day_of_month(
            frequency,
            day_of_month,
        )

        return self.repository.update(
            task_id=task_id,
            enabled=enabled,
            frequency=frequency,
            schedule_time=schedule_time,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
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

        if frequency == "hourly":
            if now.strftime("%M") != schedule_time[-2:]:
                return False

        elif frequency == "daily":
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

        elif frequency == "monthly":
            if (
                now.day
                != schedule["day_of_month"]
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

        if frequency == "hourly":
            return (
                last_run.replace(
                    minute=0,
                    second=0,
                    microsecond=0,
                )
                != now.replace(
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            )

        if frequency == "daily":
            return last_run.date() != now.date()

        if frequency == "weekly":
            return last_run.date() != now.date()

        if frequency == "monthly":
            return (
                last_run.year != now.year
                or last_run.month != now.month
            )

        return True

    def next_run(
        self,
        schedule,
        now=None,
    ):
        if not schedule["enabled"]:
            return None

        frequency = schedule["frequency"]

        if frequency == "manual":
            return None

        if now is None:
            now = datetime.now()

        schedule_time = schedule["schedule_time"]

        if schedule_time is None:
            return None

        hour, minute = (
            int(value)
            for value in schedule_time.split(":")
        )

        if frequency == "hourly":
            candidate = now.replace(
                minute=minute,
                second=0,
                microsecond=0,
            )

            if candidate <= now:
                candidate = candidate.replace(
                    hour=(candidate.hour + 1) % 24,
                )

                if candidate.hour == 0:
                    from datetime import timedelta

                    candidate = candidate + timedelta(
                        days=1,
                    )

            return candidate

        if frequency == "daily":
            candidate = now.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0,
            )

            if candidate <= now:
                from datetime import timedelta

                candidate = candidate + timedelta(
                    days=1,
                )

            return candidate

        if frequency == "weekly":
            sunday_based_weekday = (
                now.weekday() + 1
            ) % 7

            days_ahead = (
                schedule["day_of_week"]
                - sunday_based_weekday
            ) % 7

            candidate = now.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0,
            )

            from datetime import timedelta

            candidate = candidate + timedelta(
                days=days_ahead,
            )

            if candidate <= now:
                candidate = candidate + timedelta(
                    days=7,
                )

            return candidate

        if frequency == "monthly":
            from calendar import monthrange
            from datetime import timedelta

            day = schedule["day_of_month"]

            if day is None:
                return None

            year = now.year
            month = now.month

            while True:
                last_day = monthrange(
                    year,
                    month,
                )[1]

                if day <= last_day:
                    candidate = now.replace(
                        year=year,
                        month=month,
                        day=day,
                        hour=hour,
                        minute=minute,
                        second=0,
                        microsecond=0,
                    )

                    if candidate > now:
                        return candidate

                if month == 12:
                    year += 1
                    month = 1
                else:
                    month += 1

        return None

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


    def _validate_day_of_month(
        self,
        frequency,
        day_of_month,
    ):
        if frequency != "monthly":
            if day_of_month is not None:
                raise ValueError(
                    "Day of month is only valid for monthly schedules"
                )

            return

        if day_of_month is None:
            raise ValueError(
                "Monthly schedules require a day of month"
            )

        if not isinstance(
            day_of_month,
            int,
        ):
            raise ValueError(
                "Day of month must be an integer from 1 to 31"
            )

        if day_of_month < 1 or day_of_month > 31:
            raise ValueError(
                "Day of month must be an integer from 1 to 31"
            )
