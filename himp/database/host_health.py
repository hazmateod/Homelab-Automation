"""
Host Health Repository.
"""

import json

from himp.database.database import Database


class HostHealthRepository:
    """
    Persists host health check results.
    """

    def __init__(self):

        self.database = Database()

        self.initialize()

    def initialize(self):

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS host_health_history
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                hostname TEXT NOT NULL,

                check_name TEXT NOT NULL,

                status TEXT NOT NULL,

                message TEXT,

                duration_ms REAL NOT NULL,

                details TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def save(
        self,
        hostname,
        result,
    ):

        self.database.execute(
            """
            INSERT INTO host_health_history
            (
                hostname,
                check_name,
                status,
                message,
                duration_ms,
                details
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
                hostname,
                result.check,
                result.status.value,
                result.message,
                result.duration_ms,
                json.dumps(result.details),
            ),
        )

    def latest(
        self,
        hostname,
        check=None,
    ):

        if check:

            rows = self.database.query(
                """
                SELECT *
                FROM host_health_history
                WHERE hostname=?
                AND check_name=?
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    hostname,
                    check,
                ),
            )

        else:

            rows = self.database.query(
                """
                SELECT *
                FROM host_health_history
                WHERE hostname=?
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    hostname,
                ),
            )

        if not rows:

            return None

        result = dict(rows[0])

        try:

            result["details"] = json.loads(
                result.get("details") or "{}"
            )

        except (
            TypeError,
            json.JSONDecodeError,
        ):

            result["details"] = {}

        return result

    def host(
        self,
        hostname,
        limit=50,
    ):

        rows = self.database.query(
            """
            SELECT *
            FROM host_health_history
            WHERE hostname=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                hostname,
                limit,
            ),
        )

        return [
            self._deserialize(row)
            for row in rows
        ]

    def history(
        self,
        limit=50,
    ):

        rows = self.database.query(
            """
            SELECT *
            FROM host_health_history
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

    @staticmethod
    def _deserialize(row):

        result = dict(row)

        try:

            result["details"] = json.loads(
                result.get("details") or "{}"
            )

        except (
            TypeError,
            json.JSONDecodeError,
        ):

            result["details"] = {}

        return result
