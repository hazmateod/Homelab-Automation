"""
Automation execution lock repository.
"""

from datetime import datetime, timedelta, timezone

from himp.database.database import Database


class AutomationLockRepository:
    """
    Persists automation execution locks.

    Locks are lease-based so a crashed process cannot
    permanently prevent future execution.
    """

    DEFAULT_LEASE_SECONDS = 300

    def __init__(self):
        self.database = Database()
        self._ensure_table()

    def _ensure_table(self):
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS automation_locks
            (
                task_id TEXT PRIMARY KEY,
                locked_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL
            )
            """
        )

    def acquire(
        self,
        task_id,
        lease_seconds=None,
    ):
        if lease_seconds is None:
            lease_seconds = (
                self.DEFAULT_LEASE_SECONDS
            )

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        expires_at = (
            now
            + timedelta(
                seconds=lease_seconds
            )
        )

        connection = self.database.connection

        try:
            connection.execute(
                "BEGIN IMMEDIATE"
            )

            connection.execute(
                """
                DELETE FROM automation_locks
                WHERE expires_at <= ?
                """,
                (now,),
            )

            connection.execute(
                """
                INSERT INTO automation_locks
                (
                    task_id,
                    locked_at,
                    expires_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    task_id,
                    now,
                    expires_at,
                ),
            )

            connection.commit()

            return True

        except Exception:
            connection.rollback()
            return False

    def release(
        self,
        task_id,
    ):
        self.database.execute(
            """
            DELETE FROM automation_locks
            WHERE task_id=?
            """,
            (task_id,),
        )

    def get(
        self,
        task_id,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM automation_locks
            WHERE task_id=?
            LIMIT 1
            """,
            (task_id,),
        )

        if not rows:
            return None

        return dict(rows[0])
