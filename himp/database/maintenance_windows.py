"""
Maintenance Window Repository.

Persists administrator-defined execution blackout windows.

Maintenance windows do not own scheduler or remediation lifecycle
state. They provide a durable execution-safety boundary consumed by
scheduled execution paths.
"""

from datetime import datetime, timezone

from himp.database.factory import create_database


class MaintenanceWindowRepository:
    """
    Durable maintenance-window persistence.
    """

    def __init__(
        self,
        database=None,
    ):
        self.database = (
            database
            if database is not None
            else create_database()
        )

        self.initialize()

    def initialize(self):
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS maintenance_windows
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL,

                reason TEXT NOT NULL,

                task_id TEXT,

                starts_at TIMESTAMP NOT NULL,
                ends_at TIMESTAMP NOT NULL,

                enabled INTEGER NOT NULL DEFAULT 1,

                created_by TEXT NOT NULL,

                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,

                CHECK (enabled IN (0, 1))
            )
            """
        )

    @staticmethod
    def _now():
        return datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )

    def create(
        self,
        name,
        reason,
        starts_at,
        ends_at,
        created_by,
        task_id=None,
        enabled=True,
    ):
        now = self._now()

        window_id = self.database.execute_insert(
            """
            INSERT INTO maintenance_windows
            (
                name,
                reason,
                task_id,
                starts_at,
                ends_at,
                enabled,
                created_by,
                created_at,
                updated_at
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
                name,
                reason,
                task_id,
                starts_at,
                ends_at,
                int(bool(enabled)),
                created_by,
                now,
                now,
            ),
        )

        return self.find(
            window_id
        )

    def find(
        self,
        window_id,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM maintenance_windows
            WHERE id=?
            LIMIT 1
            """,
            (
                window_id,
            ),
        )

        if not rows:
            return None

        return self._deserialize(
            rows[0]
        )

    def list(
        self,
        limit=100,
        enabled=None,
    ):
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < 1
        ):
            raise ValueError(
                "limit must be a positive integer"
            )

        parameters = []

        query = """
            SELECT *
            FROM maintenance_windows
        """

        if enabled is not None:
            query += """
                WHERE enabled=?
            """

            parameters.append(
                int(bool(enabled))
            )

        query += """
            ORDER BY starts_at ASC, id ASC
            LIMIT ?
        """

        parameters.append(
            limit
        )

        return [
            self._deserialize(row)
            for row in self.database.query(
                query,
                tuple(parameters),
            )
        ]

    def active(
        self,
        now=None,
        task_id=None,
    ):
        if now is None:
            now = self._now()

        parameters = [
            now,
            now,
        ]

        task_clause = ""

        if task_id is not None:
            task_clause = """
              AND (
                    task_id IS NULL
                    OR task_id=?
              )
            """

            parameters.append(
                task_id
            )

        else:
            task_clause = """
              AND task_id IS NULL
            """

        rows = self.database.query(
            f"""
            SELECT *
            FROM maintenance_windows
            WHERE enabled=1
              AND starts_at<=?
              AND ends_at>?
              {task_clause}
            ORDER BY
                CASE
                    WHEN task_id IS NULL
                    THEN 0
                    ELSE 1
                END,
                starts_at ASC,
                id ASC
            """,
            tuple(parameters),
        )

        return [
            self._deserialize(row)
            for row in rows
        ]

    def active_all(
        self,
        now=None,
    ):
        """
        Return every enabled maintenance window active at the
        supplied time, regardless of task scope.

        This is a visibility/query operation. Scheduled execution
        enforcement continues to use active(task_id=...) so that
        task-specific windows only affect their intended task.
        """
        if now is None:
            now = self._now()

        rows = self.database.query(
            """
            SELECT *
            FROM maintenance_windows
            WHERE enabled=1
              AND starts_at<=?
              AND ends_at>?
            ORDER BY
                starts_at ASC,
                id ASC
            """,
            (
                now,
                now,
            ),
        )

        return [
            self._deserialize(row)
            for row in rows
        ]

    def upcoming(
        self,
        now=None,
        limit=25,
    ):
        if now is None:
            now = self._now()

        return [
            self._deserialize(row)
            for row in self.database.query(
                """
                SELECT *
                FROM maintenance_windows
                WHERE enabled=1
                  AND starts_at>?
                ORDER BY starts_at ASC, id ASC
                LIMIT ?
                """,
                (
                    now,
                    limit,
                ),
            )
        ]

    def set_enabled(
        self,
        window_id,
        enabled,
    ):
        now = self._now()

        affected = self.database.execute_affected(
            """
            UPDATE maintenance_windows
            SET
                enabled=?,
                updated_at=?
            WHERE id=?
            """,
            (
                int(bool(enabled)),
                now,
                window_id,
            ),
        )

        if affected == 0:
            raise KeyError(
                "maintenance window does not exist: "
                f"{window_id}"
            )

        return self.find(
            window_id
        )

    @staticmethod
    def _deserialize(
        row,
    ):
        return {
            "id": row["id"],
            "name": row["name"],
            "reason": row["reason"],
            "task_id": row["task_id"],
            "starts_at": row["starts_at"],
            "ends_at": row["ends_at"],
            "enabled": bool(
                row["enabled"]
            ),
            "created_by": row["created_by"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
