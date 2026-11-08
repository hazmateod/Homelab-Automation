"""
Automation execution lock repository.
"""

from datetime import datetime, timedelta, timezone

from himp.database.factory import create_database


class AutomationLockRepository:
    """
    Persists automation execution locks.

    Locks are lease-based so a crashed process cannot
    permanently prevent future execution.
    """

    DEFAULT_LEASE_SECONDS = 300

    def __init__(self):
        self.database = create_database()
        self._ensure_table()

    def _ensure_table(self):
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS automation_locks
            (
                task_id TEXT PRIMARY KEY,
                execution_token TEXT,
                locked_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL
            )
            """
        )

        columns = self.database.table_columns(
            "automation_locks"
        )

        if "execution_token" not in columns:
            self.database.execute(
                """
                ALTER TABLE automation_locks
                ADD COLUMN execution_token TEXT
                """
            )

    def acquire(
        self,
        task_id,
        lease_seconds=None,
        execution_token=None,
    ):
        if not isinstance(execution_token, str) or not execution_token.strip():
            raise ValueError(
                "Non-empty execution token required to acquire automation lock"
            )

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

        try:
            with self.database.transaction() as connection:
                self.database.begin_lock_transaction(
                    connection
                )

                self.database.execute_transaction(
                    connection,
                    """
                    DELETE FROM automation_locks
                    WHERE expires_at <= ?
                    """,
                    (now,),
                )

                self.database.execute_transaction(
                    connection,
                    """
                    INSERT INTO automation_locks
                    (
                        task_id,
                        execution_token,
                        locked_at,
                        expires_at
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        task_id,
                        execution_token,
                        now,
                        expires_at,
                    ),
                )

            return True

        except Exception:
            return False

    def release(
        self,
        task_id,
        execution_token=None,
    ):
        if execution_token is None:
            raise ValueError(
                "Execution token required to release automation lock"
            )

        return self.database.execute_affected(
            """
            DELETE FROM automation_locks
            WHERE task_id=?
              AND execution_token=?
            """,
            (task_id, execution_token),
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
