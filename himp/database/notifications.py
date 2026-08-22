"""
Notification Repository.

Persists transport-independent notification events, routing decisions,
suppression state, acknowledgement state, and recovery state.
"""

import json
from datetime import datetime, timezone

from himp.database.factory import create_database


class NotificationRepository:
    LIFECYCLE_STATUSES = {
        "PENDING",
        "SUPPRESSED",
        "ACKNOWLEDGED",
        "RECOVERED",
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
            CREATE TABLE IF NOT EXISTS notifications
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                event_type TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                severity TEXT NOT NULL,

                title TEXT NOT NULL,
                message TEXT NOT NULL,

                deduplication_key TEXT NOT NULL,
                correlation_key TEXT NOT NULL,

                lifecycle_status TEXT NOT NULL,
                routing_decision TEXT NOT NULL,
                logical_destinations TEXT NOT NULL,
                suppression_reason TEXT,

                metadata TEXT NOT NULL,

                occurred_at TIMESTAMP NOT NULL,

                acknowledged_by TEXT,
                acknowledged_at TIMESTAMP,

                recovered_at TIMESTAMP,

                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,

                CHECK (
                    lifecycle_status IN (
                        'PENDING',
                        'SUPPRESSED',
                        'ACKNOWLEDGED',
                        'RECOVERED'
                    )
                ),

                CHECK (
                    routing_decision IN (
                        'ROUTE',
                        'SUPPRESS'
                    )
                )
            )
            """
        )

    def create(
        self,
        event,
        *,
        lifecycle_status,
        routing_decision,
        logical_destinations,
        suppression_reason=None,
    ):
        self._validate_lifecycle_status(
            lifecycle_status
        )

        if routing_decision not in {
            "ROUTE",
            "SUPPRESS",
        }:
            raise ValueError(
                "routing_decision must be ROUTE or SUPPRESS"
            )

        now = self._now()

        notification_id = (
            self.database.execute_insert(
                """
                INSERT INTO notifications
                (
                    event_type,
                    source_type,
                    source_id,
                    severity,
                    title,
                    message,
                    deduplication_key,
                    correlation_key,
                    lifecycle_status,
                    routing_decision,
                    logical_destinations,
                    suppression_reason,
                    metadata,
                    occurred_at,
                    created_at,
                    updated_at
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
                    ?,
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
                    event.event_type,
                    event.source_type,
                    event.source_id,
                    event.severity,
                    event.title,
                    event.message,
                    event.deduplication_key,
                    event.correlation_key,
                    lifecycle_status,
                    routing_decision,
                    json.dumps(
                        list(logical_destinations)
                    ),
                    suppression_reason,
                    json.dumps(event.metadata),
                    event.occurred_at,
                    now,
                    now,
                ),
            )
        )

        return self.find(
            notification_id
        )

    def find(
        self,
        notification_id,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM notifications
            WHERE id=?
            LIMIT 1
            """,
            (
                notification_id,
            ),
        )

        if not rows:
            return None

        return self._deserialize(
            rows[0]
        )

    def list(
        self,
        limit=100,
        lifecycle_status=None,
    ):
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < 1
        ):
            raise ValueError(
                "limit must be a positive integer"
            )

        parameters = []
        query = """
            SELECT *
            FROM notifications
        """

        if lifecycle_status is not None:
            self._validate_lifecycle_status(
                lifecycle_status
            )
            query += """
                WHERE lifecycle_status=?
            """
            parameters.append(
                lifecycle_status
            )

        query += """
            ORDER BY id DESC
            LIMIT ?
        """

        parameters.append(limit)

        return [
            self._deserialize(row)
            for row in self.database.query(
                query,
                tuple(parameters),
            )
        ]

    def active_for_deduplication(
        self,
        deduplication_key,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM notifications
            WHERE deduplication_key=?
              AND lifecycle_status IN (
                  'PENDING',
                  'ACKNOWLEDGED'
              )
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                deduplication_key,
            ),
        )

        if not rows:
            return None

        return self._deserialize(
            rows[0]
        )

    def recover_correlation(
        self,
        correlation_key,
        recovered_at=None,
    ):
        if recovered_at is None:
            recovered_at = self._now()

        self.database.execute_affected(
            """
            UPDATE notifications
            SET
                lifecycle_status='RECOVERED',
                recovered_at=?,
                updated_at=?
            WHERE correlation_key=?
              AND lifecycle_status IN (
                  'PENDING',
                  'ACKNOWLEDGED'
              )
            """,
            (
                recovered_at,
                recovered_at,
                correlation_key,
            ),
        )

    def acknowledge(
        self,
        notification_id,
        acknowledged_by,
    ):
        if (
            not isinstance(
                acknowledged_by,
                str,
            )
            or not acknowledged_by.strip()
        ):
            raise ValueError(
                "acknowledged_by is required"
            )

        now = self._now()

        affected = (
            self.database.execute_affected(
                """
                UPDATE notifications
                SET
                    lifecycle_status='ACKNOWLEDGED',
                    acknowledged_by=?,
                    acknowledged_at=?,
                    updated_at=?
                WHERE id=?
                  AND lifecycle_status='PENDING'
                """,
                (
                    acknowledged_by.strip(),
                    now,
                    now,
                    notification_id,
                ),
            )
        )

        if affected == 0:
            existing = self.find(
                notification_id
            )

            if existing is None:
                raise KeyError(
                    "notification does not exist: "
                    f"{notification_id}"
                )

            raise ValueError(
                "only a pending notification "
                "can be acknowledged"
            )

        return self.find(
            notification_id
        )

    @classmethod
    def _validate_lifecycle_status(
        cls,
        lifecycle_status,
    ):
        if lifecycle_status not in (
            cls.LIFECYCLE_STATUSES
        ):
            raise ValueError(
                "invalid notification lifecycle status: "
                f"{lifecycle_status}"
            )

    @staticmethod
    def _deserialize(
        row,
    ):
        return {
            "id": row["id"],
            "event_type": row["event_type"],
            "source_type": row["source_type"],
            "source_id": row["source_id"],
            "severity": row["severity"],
            "title": row["title"],
            "message": row["message"],
            "deduplication_key": (
                row["deduplication_key"]
            ),
            "correlation_key": (
                row["correlation_key"]
            ),
            "lifecycle_status": (
                row["lifecycle_status"]
            ),
            "routing_decision": (
                row["routing_decision"]
            ),
            "logical_destinations": (
                json.loads(
                    row["logical_destinations"]
                )
            ),
            "suppression_reason": (
                row["suppression_reason"]
            ),
            "metadata": (
                json.loads(row["metadata"])
            ),
            "occurred_at": row["occurred_at"],
            "acknowledged_by": (
                row["acknowledged_by"]
            ),
            "acknowledged_at": (
                row["acknowledged_at"]
            ),
            "recovered_at": (
                row["recovered_at"]
            ),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
