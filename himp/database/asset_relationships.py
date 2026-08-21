"""
Asset Relationship Repository.

Stores deterministic relationships between infrastructure assets.
"""

from himp.database.factory import create_database


class AssetRelationshipRepository:
    """
    Asset relationship data access layer.
    """

    def __init__(self):
        self.database = create_database()
        self.initialize()

    def initialize(self):
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS asset_relationships
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                source_type TEXT NOT NULL,

                source_id TEXT NOT NULL,

                relationship_type TEXT NOT NULL,

                target_type TEXT NOT NULL,

                target_id TEXT NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(
                    source_type,
                    source_id,
                    relationship_type,
                    target_type,
                    target_id
                )
            )
            """
        )

    def add(
        self,
        source_type,
        source_id,
        relationship_type,
        target_type,
        target_id,
    ):
        existing = self.database.query(
            """
            SELECT *
            FROM asset_relationships
            WHERE source_type=?
              AND source_id=?
              AND relationship_type=?
              AND target_type=?
              AND target_id=?
            LIMIT 1
            """,
            (
                source_type,
                source_id,
                relationship_type,
                target_type,
                target_id,
            ),
        )

        if existing:
            raise ValueError(
                "Asset relationship already exists"
            )

        self.database.execute(
            """
            INSERT INTO asset_relationships
            (
                source_type,
                source_id,
                relationship_type,
                target_type,
                target_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                source_type,
                source_id,
                relationship_type,
                target_type,
                target_id,
            ),
        )

        rows = self.database.query(
            """
            SELECT
                source_type,
                source_id,
                relationship_type,
                target_type,
                target_id
            FROM asset_relationships
            WHERE source_type=?
              AND source_id=?
              AND relationship_type=?
              AND target_type=?
              AND target_id=?
            LIMIT 1
            """,
            (
                source_type,
                source_id,
                relationship_type,
                target_type,
                target_id,
            ),
        )

        return rows[0]

    def remove(
        self,
        source_type,
        source_id,
        relationship_type,
        target_type,
        target_id,
    ):
        self.database.execute(
            """
            DELETE FROM asset_relationships
            WHERE source_type=?
              AND source_id=?
              AND relationship_type=?
              AND target_type=?
              AND target_id=?
            """,
            (
                source_type,
                source_id,
                relationship_type,
                target_type,
                target_id,
            ),
        )

    def list(self):
        return self.database.query(
            """
            SELECT
                source_type,
                source_id,
                relationship_type,
                target_type,
                target_id
            FROM asset_relationships
            ORDER BY id
            """
        )

    def list_for_source(
        self,
        source_type,
        source_id,
    ):
        return self.database.query(
            """
            SELECT
                source_type,
                source_id,
                relationship_type,
                target_type,
                target_id
            FROM asset_relationships
            WHERE source_type=?
              AND source_id=?
            ORDER BY id
            """,
            (
                source_type,
                source_id,
            ),
        )

    def list_for_target(
        self,
        target_type,
        target_id,
    ):
        return self.database.query(
            """
            SELECT
                source_type,
                source_id,
                relationship_type,
                target_type,
                target_id
            FROM asset_relationships
            WHERE target_type=?
              AND target_id=?
            ORDER BY id
            """,
            (
                target_type,
                target_id,
            ),
        )
