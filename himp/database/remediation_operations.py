"""
Remediation Operations Repository.

Persists operational configuration for scheduled remediation.
"""

import json

from himp.database.factory import create_database


class RemediationOperationsRepository:
    """
    Persists remediation operational configuration.
    """

    def __init__(
        self,
        database=None,
    ):
        if database is None:
            database = create_database()

        self.database = database
        self.initialize()

    def initialize(self):
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS remediation_operations
            (
                id INTEGER PRIMARY KEY CHECK (id = 1),

                enabled INTEGER NOT NULL DEFAULT 0,

                source_type TEXT NOT NULL,

                source_id TEXT NOT NULL,

                baseline TEXT,

                change_limit INTEGER NOT NULL DEFAULT 10,

                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def get(self):
        rows = self.database.query(
            """
            SELECT *
            FROM remediation_operations
            WHERE id=1
            LIMIT 1
            """
        )

        if not rows:
            return None

        return self._deserialize(
            rows[0]
        )

    def save(
        self,
        enabled,
        source_type,
        source_id,
        baseline=None,
        change_limit=10,
    ):
        self.database.execute(
            """
            INSERT INTO remediation_operations
            (
                id,
                enabled,
                source_type,
                source_id,
                baseline,
                change_limit
            )
            VALUES
            (
                1,
                ?,
                ?,
                ?,
                ?,
                ?
            )
            ON CONFLICT(id)
            DO UPDATE SET
                enabled=excluded.enabled,
                source_type=excluded.source_type,
                source_id=excluded.source_id,
                baseline=excluded.baseline,
                change_limit=excluded.change_limit,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                int(enabled),
                source_type,
                source_id,
                (
                    None
                    if baseline is None
                    else json.dumps(baseline)
                ),
                change_limit,
            ),
        )

        return self.get()

    @staticmethod
    def _deserialize(
        row,
    ):
        return {
            "id": row["id"],
            "enabled": bool(row["enabled"]),
            "source_type": row["source_type"],
            "source_id": row["source_id"],
            "baseline": (
                None
                if row["baseline"] is None
                else json.loads(row["baseline"])
            ),
            "change_limit": row["change_limit"],
            "updated_at": row["updated_at"],
        }
