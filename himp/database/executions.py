"""
Execution Repository.
"""

import json

from himp.database.database import Database


class ExecutionRepository:

    def __init__(self):

        self.database = Database()

    def save(self, execution):

        self.database.execute(
            """
            INSERT INTO executions
            (
                plugin,
                success,
                return_code,
                elapsed,
                stdout,
                stderr,
                warnings,
                artifacts
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
                ?
            )
            """,
            (
                execution.plugin,
                int(execution.success),
                execution.return_code,
                execution.elapsed,
                execution.stdout,
                execution.stderr,
                json.dumps(execution.warnings),
                json.dumps(execution.artifacts),
            ),
        )

    def find(self, execution_id):

        rows = self.database.query(
            """
            SELECT *
            FROM executions
            WHERE id=?
            LIMIT 1
            """,
            (
                execution_id,
            ),
        )

        if not rows:

            return None

        return dict(rows[0])

    def latest(self, plugin):

        rows = self.database.query(
            """
            SELECT *
            FROM executions
            WHERE plugin=?
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                plugin,
            ),
        )

        if not rows:

            return None

        return dict(rows[0])

    def history(self, limit=50):

        rows = self.database.query(
            """
            SELECT *
            FROM executions
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                limit,
            ),
        )

        return [dict(row) for row in rows]
