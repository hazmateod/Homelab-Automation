"""
Inventory Repository.

Stores inventory snapshots and tracks changes.
"""

from datetime import datetime, timezone

from himp.database.database import Database


class InventoryRepository:
    """
    Inventory data access layer.
    """

    def __init__(self):

        self.database = Database()

        self.initialize()

    def initialize(self):

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory_hosts
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                hostname TEXT NOT NULL UNIQUE,

                group_name TEXT,

                ip TEXT,

                ansible_user TEXT,

                become INTEGER NOT NULL,

                active INTEGER NOT NULL DEFAULT 1,

                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory_changes
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                hostname TEXT NOT NULL,

                change_type TEXT NOT NULL,

                field TEXT,

                old_value TEXT,

                new_value TEXT,

                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        columns = self.database.table_columns(
            "inventory_hosts"
        )

        if "active" not in columns:

            self.database.execute(
                """
                ALTER TABLE inventory_hosts
                ADD COLUMN active INTEGER NOT NULL DEFAULT 1
                """
            )

    def save_snapshot(
        self,
        hosts,
    ):

        current = {
            host["hostname"]
            for host in hosts
        }

        existing = self.all_hosts(
            include_inactive=True
        )

        for host in hosts:

            self.save_host(host)

        for record in existing:

            if (
                record["hostname"] not in current
                and record["active"]
            ):

                self.mark_removed(
                    record["hostname"]
                )

    def save_host(
        self,
        host,
    ):

        existing = self.find_host(
            host["hostname"],
            include_inactive=True,
        )

        if existing:

            if not existing["active"]:

                self.restore_host(
                    host["hostname"]
                )

            else:

                self.detect_changes(
                    existing,
                    host,
                )

        else:

            self.record_change(
                host["hostname"],
                "ADDED",
                None,
                None,
                None,
            )

        self.database.execute(
            """
            INSERT INTO inventory_hosts
            (
                hostname,
                group_name,
                ip,
                ansible_user,
                become,
                active,
                last_seen
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                1,
                ?
            )
            ON CONFLICT(hostname)
            DO UPDATE SET

                group_name=excluded.group_name,
                ip=excluded.ip,
                ansible_user=excluded.ansible_user,
                become=excluded.become,
                active=1,
                last_seen=excluded.last_seen
            """,
            (
                host["hostname"],
                host["group"],
                host["ip"],
                host["user"],
                int(host["become"]),
                datetime.now(timezone.utc).replace(tzinfo=None),
            ),
        )

    def mark_removed(
        self,
        hostname,
    ):

        self.database.execute(
            """
            UPDATE inventory_hosts
            SET active=0
            WHERE hostname=?
            """,
            (
                hostname,
            ),
        )

        self.record_change(
            hostname,
            "REMOVED",
            None,
            None,
            None,
        )

    def restore_host(
        self,
        hostname,
    ):
        self.database.execute(
            """
            UPDATE inventory_hosts
            SET active=1,
                last_seen=?
            WHERE hostname=?
            """,
            (
                datetime.now(timezone.utc).replace(tzinfo=None),
                hostname,
            ),
        )

        self.record_change(
            hostname,
            "RESTORED",
            None,
            None,
            None,
        )

        return self.find_host(
            hostname,
            include_inactive=True,
        )

    def detect_changes(
        self,
        old,
        new,
    ):

        fields = [
            ("group_name", "group"),
            ("ip", "ip"),
            ("ansible_user", "user"),
        ]

        for database_field, new_field in fields:

            old_value = old[database_field]

            new_value = new[new_field]

            if old_value != new_value:

                self.record_change(
                    new["hostname"],
                    "UPDATED",
                    database_field,
                    old_value,
                    new_value,
                )

        old_become = bool(
            old["become"]
        )

        new_become = bool(
            new["become"]
        )

        if old_become != new_become:

            self.record_change(
                new["hostname"],
                "UPDATED",
                "become",
                old_become,
                new_become,
            )

    def record_change(
        self,
        hostname,
        change_type,
        field,
        old_value,
        new_value,
    ):

        existing = self.database.query(
            """
            SELECT *
            FROM inventory_changes
            WHERE hostname=?
            AND change_type=?
            AND field IS ?
            AND old_value IS ?
            AND new_value IS ?
            LIMIT 1
            """,
            (
                hostname,
                change_type,
                field,
                old_value,
                new_value,
            ),
        )

        if existing:

            return

        self.database.execute(
            """
            INSERT INTO inventory_changes
            (
                hostname,
                change_type,
                field,
                old_value,
                new_value
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
                hostname,
                change_type,
                field,
                old_value,
                new_value,
            ),
        )

    def all_hosts(
        self,
        include_inactive=False,
    ):

        if include_inactive:

            return self.database.query(
                """
                SELECT *
                FROM inventory_hosts
                ORDER BY hostname
                """
            )

        return self.database.query(
            """
            SELECT *
            FROM inventory_hosts
            WHERE active=1
            ORDER BY hostname
            """
        )

    def find_host(
        self,
        hostname,
        include_inactive=False,
    ):

        query = """
            SELECT *
            FROM inventory_hosts
            WHERE hostname=?
        """

        if not include_inactive:

            query += " AND active=1"

        query += " LIMIT 1"

        rows = self.database.query(
            query,
            (
                hostname,
            ),
        )

        return rows[0] if rows else None

    def count(self):

        row = self.database.query(
            """
            SELECT COUNT(*) AS total
            FROM inventory_hosts
            WHERE active=1
            """
        )

        return row[0]["total"]

    def changes(
        self,
        limit=100,
    ):

        return self.database.query(
            """
            SELECT *
            FROM inventory_changes
            ORDER BY changed_at DESC,
                     id DESC
            LIMIT ?
            """,
            (
                limit,
            ),
        )
