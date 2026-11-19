"""Additive host identity and incarnation history for shadow reads."""

from uuid import uuid4

from himp.database.inventory import InventoryRepository


class HostIdentityRepository:
    def __init__(self, inventory=None):
        self.database = (inventory or InventoryRepository()).database
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS host_identities (
                host_id TEXT PRIMARY KEY,
                inventory_id BIGINT NOT NULL UNIQUE,
                original_hostname TEXT NOT NULL,
                current_incarnation INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS host_incarnations (
                host_id TEXT NOT NULL REFERENCES host_identities(host_id),
                incarnation INTEGER NOT NULL,
                source TEXT NOT NULL,
                recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (host_id, incarnation)
            )
            """
        )

    def backfill(self):
        """Create an identity for each known inventory row, including retired hosts."""
        with self.database.transaction() as connection:
            missing = self.database.execute_transaction(
                connection,
                """
                SELECT inventory_hosts.id, inventory_hosts.hostname
                FROM inventory_hosts
                LEFT JOIN host_identities ON host_identities.inventory_id=inventory_hosts.id
                WHERE host_identities.host_id IS NULL
                ORDER BY inventory_hosts.id
                """,
            ).fetchall()
            count = 0
            for row in missing:
                created = self.database.execute_transaction(
                    connection,
                    """
                    INSERT INTO host_identities (host_id, inventory_id, original_hostname)
                    VALUES (?, ?, ?) ON CONFLICT (inventory_id) DO NOTHING
                    RETURNING host_id
                    """,
                    (str(uuid4()), row["id"], row["hostname"]),
                ).fetchone()
                if created is not None:
                    self._record_incarnation(connection, created["host_id"], 1, "inventory_backfill")
                    count += 1
        return count

    def _record_incarnation(self, connection, host_id, incarnation, source):
        self.database.execute_transaction(
            connection,
            """
            INSERT INTO host_incarnations (host_id, incarnation, source)
            VALUES (?, ?, ?)
            """,
            (host_id, incarnation, source),
        )

    def record_rebuild(self, host_id, expected_incarnation):
        """Advance only after an operator verifies replacement of the current host."""
        with self.database.transaction() as connection:
            updated = self.database.execute_transaction(
                connection,
                """
                UPDATE host_identities
                SET current_incarnation=current_incarnation+1
                WHERE host_id=? AND current_incarnation=?
                  AND EXISTS (
                      SELECT 1 FROM inventory_hosts
                      WHERE inventory_hosts.id=host_identities.inventory_id
                        AND inventory_hosts.active=1
                  )
                RETURNING current_incarnation
                """,
                (host_id, expected_incarnation),
            ).fetchone()
            if updated is None:
                return None
            incarnation = updated["current_incarnation"]
            self._record_incarnation(connection, host_id, incarnation, "verified_rebuild")
            return incarnation

    def current(self):
        """Return the active inventory projection in one query."""
        return self.database.query(
            """
            SELECT host_identities.host_id, host_identities.current_incarnation,
                   inventory_hosts.hostname, inventory_hosts.group_name, inventory_hosts.ip
            FROM host_identities
            JOIN inventory_hosts ON inventory_hosts.id=host_identities.inventory_id
            WHERE inventory_hosts.active=1
            ORDER BY inventory_hosts.hostname
            """
        )

    def history(self, host_id):
        return self.database.query(
            """
            SELECT incarnation, source, recorded_at
            FROM host_incarnations
            WHERE host_id=?
            ORDER BY incarnation
            """,
            (host_id,),
        )
