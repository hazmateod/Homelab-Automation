"""
Remediation Audit Repository.

Persists remediation policy decisions and execution outcomes.
"""

import json

from himp.database.database import Database


class RemediationAuditRepository:
    """
    Persists remediation audit history.
    """

    def __init__(
        self,
        database=None,
    ):
        if database is None:
            database = Database()

        self.database = database
        self.initialize()

    def initialize(self):
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS remediation_audit
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                source_type TEXT NOT NULL,

                source_id TEXT NOT NULL,

                task_id TEXT NOT NULL,

                decision TEXT NOT NULL,

                reason TEXT NOT NULL,

                evidence TEXT,

                risk_level TEXT,

                confirmation_required INTEGER NOT NULL,

                confirmed INTEGER NOT NULL,

                execution_id INTEGER,

                execution_success INTEGER,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def save(
        self,
        source_type,
        source_id,
        task_id,
        decision,
        reason,
        evidence,
        risk_level,
        confirmation_required,
        confirmed,
        execution_id=None,
        execution_success=None,
    ):
        cursor = self.database.execute(
            """
            INSERT INTO remediation_audit
            (
                source_type,
                source_id,
                task_id,
                decision,
                reason,
                evidence,
                risk_level,
                confirmation_required,
                confirmed,
                execution_id,
                execution_success
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
                ?
            )
            """,
            (
                source_type,
                source_id,
                task_id,
                decision,
                reason,
                json.dumps(evidence),
                risk_level,
                int(confirmation_required),
                int(confirmed),
                execution_id,
                (
                    None
                    if execution_success is None
                    else int(execution_success)
                ),
            ),
        )

        return self.find(
            cursor.lastrowid
        )

    def find(
        self,
        audit_id,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM remediation_audit
            WHERE id=?
            LIMIT 1
            """,
            (
                audit_id,
            ),
        )

        if not rows:
            return None

        return self._deserialize(
            rows[0]
        )

    def history(
        self,
        limit=50,
        source_type=None,
        source_id=None,
        decision=None,
    ):
        clauses = []
        parameters = []

        if source_type is not None:
            clauses.append(
                "source_type=?"
            )
            parameters.append(
                source_type
            )

        if source_id is not None:
            clauses.append(
                "source_id=?"
            )
            parameters.append(
                source_id
            )

        if decision is not None:
            clauses.append(
                "decision=?"
            )
            parameters.append(
                decision
            )

        query = """
            SELECT *
            FROM remediation_audit
        """

        if clauses:
            query += (
                " WHERE "
                + " AND ".join(clauses)
            )

        query += """
            ORDER BY id DESC
            LIMIT ?
        """

        parameters.append(
            limit
        )

        rows = self.database.query(
            query,
            tuple(parameters),
        )

        return [
            self._deserialize(row)
            for row in rows
        ]

    def summary(self):
        rows = self.database.query(
            """
            SELECT
                COUNT(*) AS total,
                SUM(
                    CASE
                        WHEN decision='ALLOW'
                        THEN 1
                        ELSE 0
                    END
                ) AS allow_count,
                SUM(
                    CASE
                        WHEN decision='DENY'
                        THEN 1
                        ELSE 0
                    END
                ) AS deny_count,
                SUM(
                    CASE
                        WHEN decision='CONFIRM_REQUIRED'
                        THEN 1
                        ELSE 0
                    END
                ) AS confirmation_required_count,
                SUM(
                    CASE
                        WHEN execution_success=1
                        THEN 1
                        ELSE 0
                    END
                ) AS execution_success_count,
                SUM(
                    CASE
                        WHEN execution_success=0
                        THEN 1
                        ELSE 0
                    END
                ) AS execution_failure_count
            FROM remediation_audit
            """
        )

        row = rows[0]

        return {
            "total": row["total"] or 0,
            "allow_count": row["allow_count"] or 0,
            "deny_count": row["deny_count"] or 0,
            "confirmation_required_count": (
                row["confirmation_required_count"] or 0
            ),
            "execution_success_count": (
                row["execution_success_count"] or 0
            ),
            "execution_failure_count": (
                row["execution_failure_count"] or 0
            ),
        }


    @staticmethod
    def _deserialize(
        row,
    ):
        return {
            "id": row["id"],
            "source_type": row["source_type"],
            "source_id": row["source_id"],
            "task_id": row["task_id"],
            "decision": row["decision"],
            "reason": row["reason"],
            "evidence": (
                json.loads(row["evidence"])
                if row["evidence"] is not None
                else {}
            ),
            "risk_level": row["risk_level"],
            "confirmation_required": bool(
                row["confirmation_required"]
            ),
            "confirmed": bool(
                row["confirmed"]
            ),
            "execution_id": row["execution_id"],
            "execution_success": (
                None
                if row["execution_success"] is None
                else bool(
                    row["execution_success"]
                )
            ),
            "created_at": row["created_at"],
        }
