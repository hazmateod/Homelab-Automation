"""
Discovery Repository.

Stores infrastructure discovery information.
"""

from datetime import datetime, timezone

from himp.database.factory import create_database


class DiscoveryRepository:

    def __init__(self):

        self.database = create_database()

        self.initialize()

    def initialize(self):

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS discovery
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                plugin TEXT NOT NULL,

                hostname TEXT NOT NULL,

                category TEXT NOT NULL,

                name TEXT NOT NULL,

                value TEXT,

                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def replace_host(
        self,
        plugin,
        hostname,
        records,
    ):

        self.database.execute(
            """
            DELETE FROM discovery
            WHERE plugin=?
            AND hostname=?
            """,
            (
                plugin,
                hostname,
            ),
        )

        for record in records:

            self.database.execute(
                """
                INSERT INTO discovery
                (
                    plugin,
                    hostname,
                    category,
                    name,
                    value,
                    discovered_at
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
                    plugin,
                    hostname,
                    record["category"],
                    record["name"],
                    record.get("value"),
                    datetime.now(timezone.utc).replace(tzinfo=None),
                ),
            )

    def all(self):

        return self.database.query(
            """
            SELECT *
            FROM discovery
            ORDER BY
                plugin,
                hostname,
                category,
                name
            """
        )

    def plugin(
        self,
        plugin,
    ):

        return self.database.query(
            """
            SELECT *
            FROM discovery
            WHERE plugin=?
            ORDER BY hostname,
                     category,
                     name
            """,
            (
                plugin,
            ),
        )

    def host(
        self,
        hostname,
    ):

        return self.database.query(
            """
            SELECT *
            FROM discovery
            WHERE hostname=?
            ORDER BY plugin,
                     category,
                     name
            """,
            (
                hostname,
            ),
        )

    def count(self):

        row = self.database.query(
            """
            SELECT COUNT(*) AS total
            FROM discovery
            """
        )

        return row[0]["total"]
