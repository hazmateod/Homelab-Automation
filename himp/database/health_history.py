"""
Health History Repository.
"""

import json

from himp.database.database import Database


class HealthHistoryRepository:

    def __init__(self):

        self.database = Database()

    def save(self, execution):

        self.database.execute(
            """
            INSERT INTO health_history
            (
                plugin,
                status,
                score,
                possible,
                issues,
                metadata
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
                execution.summary.plugin,
                execution.summary.status.value,
                execution.summary.score,
                execution.summary.possible,
                json.dumps(
                    execution.summary.issues
                ),
                json.dumps(
                    execution.metadata.data
                ),
            ),
        )

    def latest(self, plugin):

        rows = self.database.query(
            """
            SELECT *
            FROM health_history
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

    def plugin(self, plugin):

        rows = self.database.query(
            """
            SELECT *
            FROM health_history
            WHERE plugin=?
            ORDER BY id DESC
            """,
            (
                plugin,
            ),
        )

        return [
            dict(row)
            for row in rows
        ]

    def history(self, limit=50):

        rows = self.database.query(
            """
            SELECT *
            FROM health_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                limit,
            ),
        )

        return [
            dict(row)
            for row in rows
        ]
