"""
Workflow execution repository.
"""

from himp.database.factory import create_database


class WorkflowExecutionRepository:
    """
    Persists workflow execution history.
    """

    def __init__(self):
        self.database = create_database()
        self._ensure_table()

    def _ensure_table(self):
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_executions
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                workflow_id INTEGER NOT NULL,

                workflow_execution_id TEXT NOT NULL UNIQUE,

                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                completed_at TIMESTAMP,

                success INTEGER,

                current_task_id TEXT,

                replay_of_workflow_execution_id TEXT
            )
            """
        )

        column_names = self.database.table_columns(
            "workflow_executions"
        )

        if "current_task_id" not in column_names:
            self.database.execute(
                """
                ALTER TABLE workflow_executions
                ADD COLUMN current_task_id TEXT
                """
            )

        if (
            "replay_of_workflow_execution_id"
            not in column_names
        ):
            self.database.execute(
                """
                ALTER TABLE workflow_executions
                ADD COLUMN replay_of_workflow_execution_id TEXT
                """
            )

    def create(
        self,
        workflow_id,
        workflow_execution_id,
        started_at=None,
        replay_of_workflow_execution_id=None,
    ):
        self.database.execute(
            """
            INSERT INTO workflow_executions
            (
                workflow_id,
                workflow_execution_id,
                started_at,
                replay_of_workflow_execution_id
            )
            VALUES
            (
                ?,
                ?,
                COALESCE(?, CURRENT_TIMESTAMP),
                ?
            )
            """,
            (
                workflow_id,
                workflow_execution_id,
                started_at,
                replay_of_workflow_execution_id,
            ),
        )

        return self.find(
            workflow_execution_id
        )

    def find(self, workflow_execution_id):
        rows = self.database.query(
            """
            SELECT *
            FROM workflow_executions
            WHERE workflow_execution_id=?
            LIMIT 1
            """,
            (
                workflow_execution_id,
            ),
        )

        if not rows:
            return None

        return self._deserialize(rows[0])

    def history(
        self,
        limit=50,
        workflow_id=None,
    ):
        clauses = []
        parameters = []

        if workflow_id is not None:
            clauses.append("workflow_id=?")
            parameters.append(workflow_id)

        query = """
            SELECT *
            FROM workflow_executions
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
        workflow_id,
        limit=50,
    ):
        return self.history(
            limit=limit,
            workflow_id=workflow_id,
        )

    def set_current_task(
        self,
        workflow_execution_id,
        current_task_id,
    ):
        existing = self.find(
            workflow_execution_id
        )

        if existing is None:
            return None

        self.database.execute(
            """
            UPDATE workflow_executions
            SET current_task_id=?
            WHERE workflow_execution_id=?
            """,
            (
                current_task_id,
                workflow_execution_id,
            ),
        )

        return self.find(
            workflow_execution_id
        )

    def complete(
        self,
        workflow_execution_id,
        success,
        completed_at=None,
    ):
        existing = self.find(
            workflow_execution_id
        )

        if existing is None:
            return None

        self.database.execute(
            """
            UPDATE workflow_executions
            SET
                completed_at=COALESCE(
                    ?,
                    CURRENT_TIMESTAMP
                ),
                success=?,
                current_task_id=NULL
            WHERE workflow_execution_id=?
            """,
            (
                completed_at,
                int(success),
                workflow_execution_id,
            ),
        )

        return self.find(
            workflow_execution_id
        )

    @staticmethod
    def _deserialize(row):
        result = dict(row)

        if result.get("success") is not None:
            result["success"] = bool(
                result["success"]
            )

        return result
