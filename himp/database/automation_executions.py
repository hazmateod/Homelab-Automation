"""
Automation Execution Repository.
"""

import json

from himp.database.database import Database


class AutomationExecutionRepository:
    """
    Persists automation execution history.
    """

    def __init__(self):
        self.database = Database()
        self._ensure_table()

    def _ensure_table(self):
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS automation_executions
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                task_id TEXT NOT NULL,

                success INTEGER NOT NULL,

                elapsed REAL NOT NULL,

                result TEXT,

                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def save(
        self,
        task_id,
        success,
        elapsed,
        result,
        executed_at=None,
    ):
        self.database.execute(
            """
            INSERT INTO automation_executions
            (
                task_id,
                success,
                elapsed,
                result,
                executed_at
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                COALESCE(?, CURRENT_TIMESTAMP)
            )
            """,
            (
                task_id,
                int(success),
                elapsed,
                json.dumps(result),
                executed_at,
            ),
        )

    def find(self, execution_id):
        rows = self.database.query(
            """
            SELECT *
            FROM automation_executions
            WHERE id=?
            LIMIT 1
            """,
            (
                execution_id,
            ),
        )

        if not rows:
            return None

        return self._deserialize(rows[0])

    def latest(self, task_id):
        rows = self.database.query(
            """
            SELECT *
            FROM automation_executions
            WHERE task_id=?
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                task_id,
            ),
        )

        if not rows:
            return None

        return self._deserialize(rows[0])

    def history(self, limit=50):
        rows = self.database.query(
            """
            SELECT *
            FROM automation_executions
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                limit,
            ),
        )

        return [
            self._deserialize(row)
            for row in rows
        ]

    def task_history(
        self,
        task_id,
        limit=50,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM automation_executions
            WHERE task_id=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                task_id,
                limit,
            ),
        )

        return [
            self._deserialize(row)
            for row in rows
        ]

    @staticmethod
    def _deserialize(row):
        result = dict(row)

        try:
            result["result"] = json.loads(
                result.get("result") or "{}"
            )
        except (TypeError, json.JSONDecodeError):
            result["result"] = {}

        result["success"] = bool(
            result["success"]
        )

        return result
