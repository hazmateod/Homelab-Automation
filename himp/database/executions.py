"""
Execution Repository.
"""

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
                elapsed
            )
            VALUES
            (
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
            ),
        )

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
