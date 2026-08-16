"""
Scheduler Repository.

Stores HIMP automation schedule configuration.
"""

from datetime import datetime, timezone

from himp.database.database import Database


class SchedulerRepository:
    """
    Scheduler data access layer.
    """

    def __init__(self):
        self.database = Database()
        self.initialize()

    def initialize(self):
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS automation_schedules
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                task_id TEXT NOT NULL UNIQUE,

                name TEXT NOT NULL,

                description TEXT NOT NULL,

                enabled INTEGER NOT NULL DEFAULT 1,

                frequency TEXT NOT NULL DEFAULT 'manual',

                schedule_time TEXT,

                day_of_week INTEGER,

                day_of_month INTEGER,

                last_run TIMESTAMP,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        columns = {
            row[1]
            for row in self.database.query(
                "PRAGMA table_info(automation_schedules)"
            )
        }

        if "day_of_month" not in columns:
            self.database.execute(
                """
                ALTER TABLE automation_schedules
                ADD COLUMN day_of_month INTEGER
                """
            )

        self._seed(
            task_id="health_check",
            name="Health Check",
            description="Run health validation across plugins.",
            frequency="manual",
            schedule_time=None,
            day_of_week=None,
        )

        self._seed(
            task_id="host_health_check",
            name="Host Health Check",
            description="Run SSH health checks across active inventory hosts.",
            frequency="daily",
            schedule_time="03:30",
            day_of_week=None,
        )

        self._seed(
            task_id="generate_reports",
            name="Generate Reports",
            description="Generate HIMP infrastructure reports.",
            frequency="manual",
            schedule_time=None,
            day_of_week=None,
        )

        self._seed(
            task_id="inventory_refresh",
            name="Inventory Refresh",
            description="Refresh inventory data.",
            frequency="daily",
            schedule_time="03:00",
            day_of_week=None,
        )

        self._seed(
            task_id="scheduled_updates",
            name="Scheduled Updates",
            description="Run maintenance updates across the homelab.",
            frequency="daily",
            schedule_time="03:15",
            day_of_week=None,
        )

    def _seed(
        self,
        task_id,
        name,
        description,
        frequency,
        schedule_time,
        day_of_week,
        day_of_month=None,
    ):
        existing = self.database.query(
            """
            SELECT id
            FROM automation_schedules
            WHERE task_id=?
            LIMIT 1
            """,
            (
                task_id,
            ),
        )

        if existing:
            self.database.execute(
                """
                UPDATE automation_schedules
                SET
                    name=?,
                    description=?,
                    frequency=?,
                    schedule_time=?,
                    day_of_week=?,
                    day_of_month=?
                WHERE id=?
                """,
                (
                    name,
                    description,
                    frequency,
                    schedule_time,
                    day_of_week,
                    day_of_month,
                    existing[0]["id"],
                ),
            )
            return

        self.database.execute(
            """
            INSERT INTO automation_schedules
            (
                task_id,
                name,
                description,
                enabled,
                frequency,
                schedule_time,
                day_of_week,
                day_of_month
            )
            VALUES
            (
                ?,
                ?,
                ?,
                1,
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
                task_id,
                name,
                description,
                frequency,
                schedule_time,
                day_of_week,
                day_of_month,
            ),
        )

    def all(self):
        return self.database.query(
            """
            SELECT *
            FROM automation_schedules
            ORDER BY id
            """
        )

    def find(
        self,
        task_id,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM automation_schedules
            WHERE task_id=?
            LIMIT 1
            """,
            (
                task_id,
            ),
        )

        if not rows:
            return None

        return rows[0]

    def update(
        self,
        task_id,
        enabled,
        frequency,
        schedule_time,
        day_of_week,
        day_of_month,
    ):
        self.database.execute(
            """
            UPDATE automation_schedules
            SET enabled=?,
                frequency=?,
                schedule_time=?,
                day_of_week=?,
                day_of_month=?,
                updated_at=?
            WHERE task_id=?
            """,
            (
                int(enabled),
                frequency,
                schedule_time,
                day_of_week,
                day_of_month,
                datetime.now(timezone.utc).replace(tzinfo=None),
                task_id,
            ),
        )

        return self.find(task_id)

    def record_run(
        self,
        task_id,
    ):
        self.database.execute(
            """
            UPDATE automation_schedules
            SET last_run=?,
                updated_at=?
            WHERE task_id=?
            """,
            (
                datetime.now(timezone.utc).replace(tzinfo=None),
                datetime.now(timezone.utc).replace(tzinfo=None),
                task_id,
            ),
        )

        return self.find(task_id)
