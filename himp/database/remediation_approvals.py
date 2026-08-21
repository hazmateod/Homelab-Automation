"""
Remediation Approval Queue Repository.

Persists operator approval decisions independently from remediation
execution and remediation audit history.
"""

import json
from datetime import datetime, timezone

from himp.database.factory import create_database


class RemediationApprovalRepository:
    """
    Durable approval queue for remediation recommendations.
    """

    STATUSES = {
        "PENDING",
        "APPROVED",
        "DENIED",
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
            CREATE TABLE IF NOT EXISTS remediation_approvals
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                recommendation_id TEXT NOT NULL,
                task_id TEXT NOT NULL DEFAULT 'scheduled_updates',

                source_type TEXT NOT NULL,

                source_id TEXT NOT NULL,

                target_type TEXT NOT NULL,

                target_id TEXT NOT NULL,

                condition TEXT NOT NULL,

                severity TEXT NOT NULL,

                recommended_action TEXT NOT NULL,

                rationale TEXT NOT NULL,

                evidence TEXT NOT NULL,

                affected_assets TEXT NOT NULL,

                dependency_depth INTEGER,

                dependency_path TEXT NOT NULL,

                status TEXT NOT NULL DEFAULT 'PENDING',

                requested_by TEXT NOT NULL,

                decided_by TEXT,

                decision_note TEXT,

                created_at TIMESTAMP NOT NULL,

                decided_at TIMESTAMP,

                CHECK (
                    status IN (
                        'PENDING',
                        'APPROVED',
                        'DENIED'
                    )
                )
            )
            """
        )

        columns = self.database.table_columns(
            "remediation_approvals"
        )

        if "task_id" not in columns:
            self.database.execute(
                """
                ALTER TABLE remediation_approvals
                ADD COLUMN task_id TEXT
                NOT NULL DEFAULT 'scheduled_updates'
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
        recommendation,
        source_type,
        source_id,
        requested_by,
        task_id,
    ):
        if not isinstance(
            recommendation,
            dict,
        ):
            raise TypeError(
                "recommendation must be a mapping"
            )

        if (
            not isinstance(task_id, str)
            or not task_id.strip()
        ):
            raise ValueError(
                "task_id is required"
            )

        target = recommendation.get(
            "target"
        ) or {}

        recommendation_id = (
            recommendation.get(
                "recommendation_id"
            )
        )

        if not recommendation_id:
            raise ValueError(
                "recommendation_id is required"
            )

        target_type = target.get(
            "entity_type"
        )
        target_id = target.get(
            "entity_id"
        )

        if not target_type or not target_id:
            raise ValueError(
                "recommendation target is required"
            )

        approval_id = (
            self.database.execute_insert(
                """
                INSERT INTO remediation_approvals
                (
                    recommendation_id,
                    task_id,
                    source_type,
                    source_id,
                    target_type,
                    target_id,
                    condition,
                    severity,
                    recommended_action,
                    rationale,
                    evidence,
                    affected_assets,
                    dependency_depth,
                    dependency_path,
                    status,
                    requested_by,
                    created_at
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
                    'PENDING',
                    ?,
                    ?
                )
                """,
                (
                    recommendation_id,
                    task_id,
                    source_type,
                    source_id,
                    target_type,
                    target_id,
                    recommendation.get(
                        "condition",
                        "",
                    ),
                    recommendation.get(
                        "severity",
                        "INFO",
                    ),
                    recommendation.get(
                        "recommended_action",
                        "",
                    ),
                    recommendation.get(
                        "rationale",
                        "",
                    ),
                    json.dumps(
                        recommendation.get(
                            "evidence",
                            {},
                        )
                    ),
                    json.dumps(
                        recommendation.get(
                            "affected_assets",
                            [],
                        )
                    ),
                    recommendation.get(
                        "dependency_depth"
                    ),
                    json.dumps(
                        recommendation.get(
                            "dependency_path",
                            [],
                        )
                    ),
                    requested_by,
                    self._now(),
                ),
            )
        )

        return self.find(
            approval_id
        )

    def find(
        self,
        approval_id,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM remediation_approvals
            WHERE id=?
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
            FROM remediation_approvals
        """

        if status is not None:
            self._validate_status(
                status
            )
            query += " WHERE status=?"
            parameters.append(
                status
            )

        query += """
            ORDER BY id DESC
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

    def decide(
        self,
        approval_id,
        status,
        decided_by,
        decision_note=None,
    ):
        if status not in {
            "APPROVED",
            "DENIED",
        }:
            raise ValueError(
                "decision must be APPROVED or DENIED"
            )

        affected = (
            self.database.execute_affected(
                """
                UPDATE remediation_approvals
                SET
                    status=?,
                    decided_by=?,
                    decision_note=?,
                    decided_at=?
                WHERE id=?
                  AND status='PENDING'
                """,
                (
                    status,
                    decided_by,
                    decision_note,
                    self._now(),
                    approval_id,
                ),
            )
        )

        if affected == 0:
            existing = self.find(
                approval_id
            )

            if existing is None:
                raise KeyError(
                    f"approval does not exist: {approval_id}"
                )

            raise ValueError(
                "approval has already been decided"
            )

        return self.find(
            approval_id
        )

    def summary(self):
        rows = self.database.query(
            """
            SELECT
                COUNT(*) AS total,
                SUM(
                    CASE
                        WHEN status='PENDING'
                        THEN 1
                        ELSE 0
                    END
                ) AS pending,
                SUM(
                    CASE
                        WHEN status='APPROVED'
                        THEN 1
                        ELSE 0
                    END
                ) AS approved,
                SUM(
                    CASE
                        WHEN status='DENIED'
                        THEN 1
                        ELSE 0
                    END
                ) AS denied
            FROM remediation_approvals
            """
        )

        row = rows[0]

        return {
            "total": row["total"] or 0,
            "pending": row["pending"] or 0,
            "approved": row["approved"] or 0,
            "denied": row["denied"] or 0,
        }

    @classmethod
    def _validate_status(
        cls,
        status,
    ):
        if status not in cls.STATUSES:
            raise ValueError(
                f"invalid approval status: {status}"
            )

    @staticmethod
    def _deserialize(
        row,
    ):
        return {
            "id": row["id"],
            "recommendation_id": (
                row["recommendation_id"]
            ),
            "task_id": row["task_id"],
            "source_type": row["source_type"],
            "source_id": row["source_id"],
            "target_type": row["target_type"],
            "target_id": row["target_id"],
            "condition": row["condition"],
            "severity": row["severity"],
            "recommended_action": (
                row["recommended_action"]
            ),
            "rationale": row["rationale"],
            "evidence": json.loads(
                row["evidence"]
            ),
            "affected_assets": json.loads(
                row["affected_assets"]
            ),
            "dependency_depth": (
                row["dependency_depth"]
            ),
            "dependency_path": json.loads(
                row["dependency_path"]
            ),
            "status": row["status"],
            "requested_by": row[
                "requested_by"
            ],
            "decided_by": row["decided_by"],
            "decision_note": row[
                "decision_note"
            ],
            "created_at": row["created_at"],
            "decided_at": row["decided_at"],
        }
