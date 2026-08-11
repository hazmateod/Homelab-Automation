"""
Automation Dependency Repository.

Stores dependencies between HIMP automation tasks.
"""

from datetime import datetime, timezone

from himp.database.database import Database


class AutomationDependencyRepository:
    """
    Persists automation task dependencies.
    """

    def __init__(self):
        self.database = Database()
        self._ensure_table()

    def _ensure_table(self):
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS automation_dependencies
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                task_id TEXT NOT NULL,

                depends_on_task_id TEXT NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(
                    task_id,
                    depends_on_task_id
                )
            )
            """
        )

    def add(
        self,
        task_id,
        depends_on_task_id,
    ):
        if task_id == depends_on_task_id:
            raise ValueError(
                "Automation task cannot depend on itself: "
                f"{task_id}"
            )

        try:
            self.database.execute(
                """
                INSERT INTO automation_dependencies
                (
                    task_id,
                    depends_on_task_id,
                    created_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    task_id,
                    depends_on_task_id,
                    datetime.now(
                        timezone.utc
                    ).replace(tzinfo=None),
                ),
            )

        except Exception as error:
            if "UNIQUE constraint failed" in str(error):
                raise ValueError(
                    "Automation dependency already exists: "
                    f"{task_id} -> {depends_on_task_id}"
                ) from error

            raise

        return self.find(
            task_id,
            depends_on_task_id,
        )

    def remove(
        self,
        task_id,
        depends_on_task_id,
    ):
        self.database.execute(
            """
            DELETE FROM automation_dependencies
            WHERE task_id=?
              AND depends_on_task_id=?
            """,
            (
                task_id,
                depends_on_task_id,
            ),
        )

    def find(
        self,
        task_id,
        depends_on_task_id,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM automation_dependencies
            WHERE task_id=?
              AND depends_on_task_id=?
            LIMIT 1
            """,
            (
                task_id,
                depends_on_task_id,
            ),
        )

        if not rows:
            return None

        return dict(rows[0])

    def list(
        self,
        task_id,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM automation_dependencies
            WHERE task_id=?
            ORDER BY id
            """,
            (
                task_id,
            ),
        )

        return [
            dict(row)
            for row in rows
        ]

    def dependents(
        self,
        task_id,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM automation_dependencies
            WHERE depends_on_task_id=?
            ORDER BY id
            """,
            (
                task_id,
            ),
        )

        return [
            dict(row)
            for row in rows
        ]


    def all(self):
        rows = self.database.query(
            """
            SELECT *
            FROM automation_dependencies
            ORDER BY id
            """
        )

        return [
            dict(row)
            for row in rows
        ]
