"""
Notification Delivery Repository.

Persists transport delivery outcomes separately from the operational
notification lifecycle.
"""

from datetime import datetime, timezone

from himp.database.factory import create_database


class NotificationDeliveryRepository:
    STATUSES = {
        "SUCCESS",
        "FAILED",
        "SKIPPED",
    }

    def __init__(
        self,
        database=None,
    ):
        self.database = (
            database
            if database is not None
            else create_database()
        )
        self.initialize()

    @staticmethod
    def _now():
        return datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )

    def initialize(self):
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS notification_deliveries
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notification_id INTEGER NOT NULL,
                destination_type TEXT NOT NULL,
                destination_name TEXT NOT NULL,
                status TEXT NOT NULL,
                status_code INTEGER,
                error TEXT,
                attempted_at TIMESTAMP NOT NULL,

                CHECK (
                    status IN (
                        'SUCCESS',
                        'FAILED',
                        'SKIPPED'
                    )
                )
            )
            """
        )

    def record(
        self,
        *,
        notification_id,
        destination_type,
        destination_name,
        status,
        status_code=None,
        error=None,
    ):
        if status not in self.STATUSES:
            raise ValueError(
                "invalid notification delivery status: "
                f"{status}"
            )

        delivery_id = (
            self.database.execute_insert(
                """
                INSERT INTO notification_deliveries
                (
                    notification_id,
                    destination_type,
                    destination_name,
                    status,
                    status_code,
                    error,
                    attempted_at
                )
                VALUES
                (
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
                    notification_id,
                    destination_type,
                    destination_name,
                    status,
                    status_code,
                    error,
                    self._now(),
                ),
            )
        )

        return self.find(delivery_id)

    def find(
        self,
        delivery_id,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM notification_deliveries
            WHERE id=?
            LIMIT 1
            """,
            (
                delivery_id,
            ),
        )

        if not rows:
            return None

        return dict(rows[0])

    def for_notification(
        self,
        notification_id,
    ):
        return [
            dict(row)
            for row in self.database.query(
                """
                SELECT *
                FROM notification_deliveries
                WHERE notification_id=?
                ORDER BY id
                """,
                (
                    notification_id,
                ),
            )
        ]
