"""
Inventory Baseline Repository.

Stores named deterministic inventory baselines.
"""

import json


class InventoryBaselineRepository:

    def __init__(self, database=None):
        if database is None:
            from himp.database.factory import (
                create_database,
            )

            database = create_database()

        self.database = database
        self.initialize()

    def initialize(self):
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory_baselines
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                hosts TEXT NOT NULL
            )
            """
        )

    def create(
        self,
        name,
        hosts,
    ):
        existing = self.database.query(
            """
            SELECT id
            FROM inventory_baselines
            WHERE name=?
            LIMIT 1
            """,
            (
                name,
            ),
        )

        if existing:
            raise ValueError(
                f"Inventory baseline already exists: {name}"
            )

        normalized = []

        for host in hosts:
            normalized.append(
                {
                    "hostname": host["hostname"],
                    "group": host["group"],
                    "ip": host["ip"],
                    "user": host["user"],
                    "become": bool(host["become"]),
                }
            )

        normalized.sort(
            key=lambda host: host["hostname"]
        )

        self.database.execute(
            """
            INSERT INTO inventory_baselines
            (
                name,
                hosts
            )
            VALUES
            (
                ?,
                ?
            )
            """,
            (
                name,
                json.dumps(
                    normalized,
                    sort_keys=True,
                ),
            ),
        )

    def find(
        self,
        name,
    ):
        rows = self.database.query(
            """
            SELECT
                name,
                hosts
            FROM inventory_baselines
            WHERE name=?
            LIMIT 1
            """,
            (
                name,
            ),
        )

        if not rows:
            return None

        row = rows[0]

        return {
            "name": row["name"],
            "hosts": json.loads(
                row["hosts"]
            ),
        }

    def list(self):
        rows = self.database.query(
            """
            SELECT
                name,
                hosts
            FROM inventory_baselines
            ORDER BY name
            """
        )

        return [
            {
                "name": row["name"],
                "hosts": json.loads(
                    row["hosts"]
                ),
            }
            for row in rows
        ]
