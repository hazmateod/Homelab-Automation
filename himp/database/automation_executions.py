"""
Automation Execution Repository.
"""

import json

from himp.database.factory import create_database


class AutomationExecutionRepository:
    """
    Persists automation execution history.
    """

    def __init__(self):
        self.database = create_database()
        self._ensure_table()

    def _ensure_table(self):
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS automation_executions
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                task_id TEXT NOT NULL,

                workflow_execution_id TEXT,

                retry_of_execution_id INTEGER,

                retry_source_workflow_execution_id TEXT,

                success INTEGER NOT NULL,

                elapsed REAL NOT NULL,

                result TEXT,

                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        columns = self.database.table_columns(
            "automation_executions"
        )

        if "workflow_execution_id" not in columns:
            self.database.execute(
                """
                ALTER TABLE automation_executions
                ADD COLUMN workflow_execution_id TEXT
                """
            )

        if "retry_of_execution_id" not in columns:
            self.database.execute(
                """
                ALTER TABLE automation_executions
                ADD COLUMN retry_of_execution_id INTEGER
                """
            )

        if "retry_source_workflow_execution_id" not in columns:
            self.database.execute(
                """
                ALTER TABLE automation_executions
                ADD COLUMN retry_source_workflow_execution_id TEXT
                """
            )

    def save(
        self,
        task_id,
        success,
        elapsed,
        result,
        executed_at=None,
        workflow_execution_id=None,
        retry_of_execution_id=None,
        retry_source_workflow_execution_id=None,
    ):
        execution_id = self.database.execute_insert(
            """
            INSERT INTO automation_executions
            (
                task_id,
                workflow_execution_id,
                retry_of_execution_id,
                retry_source_workflow_execution_id,
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
                ?,
                ?,
                ?,
                COALESCE(?, CURRENT_TIMESTAMP)
            )
            """,
            (
                task_id,
                workflow_execution_id,
                retry_of_execution_id,
                retry_source_workflow_execution_id,
                int(success),
                elapsed,
                json.dumps(result),
                executed_at,
            ),
        )

        return execution_id

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

    def history(
        self,
        limit=50,
        task_id=None,
        success=None,
        workflow_execution_id=None,
    ):
        clauses = []
        parameters = []

        if task_id is not None:
            clauses.append("task_id=?")
            parameters.append(task_id)

        if success is not None:
            clauses.append("success=?")
            parameters.append(int(success))

        if workflow_execution_id is not None:
            clauses.append("workflow_execution_id=?")
            parameters.append(workflow_execution_id)

        query = """
            SELECT *
            FROM automation_executions
        """

        if clauses:
            query += " WHERE " + " AND ".join(
                clauses
            )

        query += """
            ORDER BY id DESC
            LIMIT ?
        """

        parameters.append(limit)

        rows = self.database.query(
            query,
            tuple(parameters),
        )

        return [
            self._deserialize(row)
            for row in rows
        ]

    def workflow_history(
        self,
        workflow_execution_id,
        limit=50,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM automation_executions
            WHERE workflow_execution_id=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                workflow_execution_id,
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
