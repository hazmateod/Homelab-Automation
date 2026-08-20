"""
Storage Capacity Repository.

Persists normalized per-filesystem capacity observations and storage
threshold state transitions.
"""

from himp.database.factory import create_database


class StorageCapacityRepository:

    def __init__(self):
        self.database = create_database()
        self.initialize()

    def initialize(self):

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS storage_capacity_history
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hostname TEXT NOT NULL,
                filesystem TEXT NOT NULL,
                mount_point TEXT NOT NULL,
                total_bytes INTEGER NOT NULL,
                used_bytes INTEGER NOT NULL,
                available_bytes INTEGER NOT NULL,
                used_percent REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS storage_alert_events
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hostname TEXT NOT NULL,
                filesystem TEXT NOT NULL,
                mount_point TEXT NOT NULL,
                previous_status TEXT,
                current_status TEXT NOT NULL,
                event_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def latest(
        self,
        hostname,
        mount_point,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM storage_capacity_history
            WHERE hostname=?
              AND mount_point=?
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                hostname,
                mount_point,
            ),
        )

        return dict(rows[0]) if rows else None

    def save(
        self,
        record,
    ):
        previous = self.latest(
            hostname=record["hostname"],
            mount_point=record["mount_point"],
        )

        self.database.execute(
            """
            INSERT INTO storage_capacity_history
            (
                hostname,
                filesystem,
                mount_point,
                total_bytes,
                used_bytes,
                available_bytes,
                used_percent,
                status
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
                record["hostname"],
                record["filesystem"],
                record["mount_point"],
                record["total_bytes"],
                record["used_bytes"],
                record["available_bytes"],
                record["used_percent"],
                record["status"],
            ),
        )

        previous_status = (
            previous["status"]
            if previous is not None
            else None
        )

        current_status = record["status"]

        transition = (
            previous_status != current_status
            and (
                previous_status is not None
                or current_status in (
                    "WARNING",
                    "CRITICAL",
                )
            )
        )

        if transition:
            event_type = (
                "RECOVERY"
                if current_status == "PASS"
                else "ALERT"
            )

            self.database.execute(
                """
                INSERT INTO storage_alert_events
                (
                    hostname,
                    filesystem,
                    mount_point,
                    previous_status,
                    current_status,
                    event_type
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
                    record["hostname"],
                    record["filesystem"],
                    record["mount_point"],
                    previous_status,
                    current_status,
                    event_type,
                ),
            )

        return {
            "previous_status": previous_status,
            "current_status": current_status,
            "transition": transition,
        }

    def current_host(
        self,
        hostname,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM storage_capacity_history
            WHERE hostname=?
            ORDER BY id DESC
            """,
            (
                hostname,
            ),
        )

        current = {}

        for row in rows:
            record = dict(row)
            mount_point = record["mount_point"]

            if mount_point not in current:
                current[mount_point] = record

        return sorted(
            current.values(),
            key=lambda item: item["mount_point"],
        )

    def current_all(self):
        rows = self.database.query(
            """
            SELECT *
            FROM storage_capacity_history
            ORDER BY id DESC
            """
        )

        current = {}

        for row in rows:
            record = dict(row)
            key = (
                record["hostname"],
                record["mount_point"],
            )

            if key not in current:
                current[key] = record

        return list(current.values())

    def host_history(
        self,
        hostname,
        limit=100,
    ):
        return [
            dict(row)
            for row in self.database.query(
                """
                SELECT *
                FROM storage_capacity_history
                WHERE hostname=?
                ORDER BY id DESC
                LIMIT ?
                """,
                (
                    hostname,
                    limit,
                ),
            )
        ]

    def alert_events(
        self,
        hostname=None,
        limit=100,
    ):
        if hostname is None:
            rows = self.database.query(
                """
                SELECT *
                FROM storage_alert_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (
                    limit,
                ),
            )
        else:
            rows = self.database.query(
                """
                SELECT *
                FROM storage_alert_events
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
            dict(row)
            for row in rows
        ]
