"""
Remediation Scheduling Repository.

Persists one-time execution schedules for individually approved
remediation recommendations.

This repository owns schedule lifecycle state only. It does not
evaluate remediation policy, execute automation, perform verification,
or create remediation audit records.
"""

from datetime import datetime, timezone

from himp.database.factory import create_database


class RemediationScheduleRepository:
    """
    Durable one-time scheduling for approved remediation queue items.
    """

    STATUSES = {
        "SCHEDULED",
        "RUNNING",
        "COMPLETED",
        "FAILED",
        "CANCELLED",
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

    def initialize(self):
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS remediation_schedules
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                approval_id INTEGER NOT NULL UNIQUE,

                scheduled_for TIMESTAMP NOT NULL,

                status TEXT NOT NULL DEFAULT 'SCHEDULED',

                scheduled_by TEXT NOT NULL,

                started_at TIMESTAMP,
                completed_at TIMESTAMP,

                audit_id INTEGER,

                error TEXT,

                cancelled_by TEXT,
                cancellation_note TEXT,
                cancelled_at TIMESTAMP,

                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,

                CHECK (
                    status IN (
                        'SCHEDULED',
                        'RUNNING',
                        'COMPLETED',
                        'FAILED',
                        'CANCELLED'
                    )
                )
            )
            """
        )

    @staticmethod
    def _now():
        return datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )

    def create(
        self,
        approval_id,
        scheduled_for,
        scheduled_by,
    ):
        now = self._now()

        schedule_id = self.database.execute_insert(
            """
            INSERT INTO remediation_schedules
            (
                approval_id,
                scheduled_for,
                status,
                scheduled_by,
                created_at,
                updated_at
            )
            VALUES
            (
                ?,
                ?,
                'SCHEDULED',
                ?,
                ?,
                ?
            )
            """,
            (
                approval_id,
                scheduled_for,
                scheduled_by,
                now,
                now,
            ),
        )

        return self.find(
            schedule_id
        )

    def find(
        self,
        schedule_id,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM remediation_schedules
            WHERE id=?
            LIMIT 1
            """,
            (
                schedule_id,
            ),
        )

        if not rows:
            return None

        return self._deserialize(
            rows[0]
        )

    def find_by_approval(
        self,
        approval_id,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM remediation_schedules
            WHERE approval_id=?
            LIMIT 1
            """,
            (
                approval_id,
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
        status=None,
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
            FROM remediation_schedules
        """

        if status is not None:
            self._validate_status(
                status
            )

            query += """
                WHERE status=?
            """

            parameters.append(
                status
            )

        query += """
            ORDER BY scheduled_for ASC, id ASC
            LIMIT ?
        """

        parameters.append(
            limit
        )

        return [
            self._deserialize(row)
            for row in self.database.query(
                query,
                tuple(parameters),
            )
        ]

    def due(
        self,
        now=None,
        limit=100,
    ):
        if now is None:
            now = self._now()

        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < 1
        ):
            raise ValueError(
                "limit must be a positive integer"
            )

        return [
            self._deserialize(row)
            for row in self.database.query(
                """
                SELECT *
                FROM remediation_schedules
                WHERE status='SCHEDULED'
                  AND scheduled_for<=?
                ORDER BY scheduled_for ASC, id ASC
                LIMIT ?
                """,
                (
                    now,
                    limit,
                ),
            )
        ]

    def claim(
        self,
        schedule_id,
        now=None,
    ):
        if now is None:
            now = self._now()

        affected = self.database.execute_affected(
            """
            UPDATE remediation_schedules
            SET
                status='RUNNING',
                started_at=?,
                error=NULL,
                updated_at=?
            WHERE id=?
              AND status='SCHEDULED'
              AND scheduled_for<=?
            """,
            (
                now,
                now,
                schedule_id,
                now,
            ),
        )

        if affected == 0:
            return None

        return self.find(
            schedule_id
        )

    def complete(
        self,
        schedule_id,
        audit_id=None,
    ):
        now = self._now()

        affected = self.database.execute_affected(
            """
            UPDATE remediation_schedules
            SET
                status='COMPLETED',
                completed_at=?,
                audit_id=?,
                error=NULL,
                updated_at=?
            WHERE id=?
              AND status='RUNNING'
            """,
            (
                now,
                audit_id,
                now,
                schedule_id,
            ),
        )

        if affected == 0:
            raise ValueError(
                "only a running remediation schedule "
                "can be completed"
            )

        return self.find(
            schedule_id
        )

    def fail(
        self,
        schedule_id,
        error,
        audit_id=None,
    ):
        now = self._now()

        affected = self.database.execute_affected(
            """
            UPDATE remediation_schedules
            SET
                status='FAILED',
                completed_at=?,
                audit_id=?,
                error=?,
                updated_at=?
            WHERE id=?
              AND status='RUNNING'
            """,
            (
                now,
                audit_id,
                str(error),
                now,
                schedule_id,
            ),
        )

        if affected == 0:
            raise ValueError(
                "only a running remediation schedule "
                "can fail"
            )

        return self.find(
            schedule_id
        )

    def cancel(
        self,
        schedule_id,
        cancelled_by,
        cancellation_note=None,
    ):
        now = self._now()

        affected = self.database.execute_affected(
            """
            UPDATE remediation_schedules
            SET
                status='CANCELLED',
                cancelled_by=?,
                cancellation_note=?,
                cancelled_at=?,
                updated_at=?
            WHERE id=?
              AND status='SCHEDULED'
            """,
            (
                cancelled_by,
                cancellation_note,
                now,
                now,
                schedule_id,
            ),
        )

        if affected == 0:
            existing = self.find(
                schedule_id
            )

            if existing is None:
                raise KeyError(
                    "remediation schedule does not exist: "
                    f"{schedule_id}"
                )

            raise ValueError(
                "only a scheduled remediation can be cancelled"
            )

        return self.find(
            schedule_id
        )

    def summary(self):
        rows = self.database.query(
            """
            SELECT
                COUNT(*) AS total,
                SUM(
                    CASE
                        WHEN status='SCHEDULED'
                        THEN 1
                        ELSE 0
                    END
                ) AS scheduled,
                SUM(
                    CASE
                        WHEN status='RUNNING'
                        THEN 1
                        ELSE 0
                    END
                ) AS running,
                SUM(
                    CASE
                        WHEN status='COMPLETED'
                        THEN 1
                        ELSE 0
                    END
                ) AS completed,
                SUM(
                    CASE
                        WHEN status='FAILED'
                        THEN 1
                        ELSE 0
                    END
                ) AS failed,
                SUM(
                    CASE
                        WHEN status='CANCELLED'
                        THEN 1
                        ELSE 0
                    END
                ) AS cancelled
            FROM remediation_schedules
            """
        )

        row = rows[0]

        return {
            "total": row["total"] or 0,
            "scheduled": row["scheduled"] or 0,
            "running": row["running"] or 0,
            "completed": row["completed"] or 0,
            "failed": row["failed"] or 0,
            "cancelled": row["cancelled"] or 0,
        }

    @classmethod
    def _validate_status(
        cls,
        status,
    ):
        if status not in cls.STATUSES:
            raise ValueError(
                f"invalid remediation schedule status: {status}"
            )

    @staticmethod
    def _deserialize(
        row,
    ):
        return {
            "id": row["id"],
            "approval_id": row["approval_id"],
            "scheduled_for": row["scheduled_for"],
            "status": row["status"],
            "scheduled_by": row["scheduled_by"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "audit_id": row["audit_id"],
            "error": row["error"],
            "cancelled_by": row["cancelled_by"],
            "cancellation_note": row[
                "cancellation_note"
            ],
            "cancelled_at": row["cancelled_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
