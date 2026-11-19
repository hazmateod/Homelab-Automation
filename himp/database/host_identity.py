"""Additive host identity and incarnation history for shadow reads."""

from uuid import uuid4

from himp.database.host_automation_policies import HostAutomationPolicyRepository
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
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS host_alias_history (
                operation_id TEXT PRIMARY KEY,
                host_id TEXT NOT NULL REFERENCES host_identities(host_id),
                change_id BIGINT NOT NULL UNIQUE,
                old_hostname TEXT NOT NULL,
                new_hostname TEXT NOT NULL,
                recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def rename(self, inventory_id, old_hostname, new_hostname, operation_id):
        """Apply a journaled rename and move the active maintenance policy atomically."""
        self.backfill()
        HostAutomationPolicyRepository(self.database)
        with self.database.transaction() as connection:
            execute = self.database.execute_transaction
            previous = execute(
                connection, "SELECT 1 FROM host_alias_history WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
            if previous is not None:
                return
            renamed = execute(
                connection,
                """
                UPDATE inventory_hosts SET hostname=?
                WHERE id=? AND hostname=? AND active=1
                RETURNING id
                """,
                (new_hostname, inventory_id, old_hostname),
            ).fetchone()
            if renamed is None:
                raise ValueError("The inventory host changed before rename recovery")
            change = execute(
                connection,
                """
                INSERT INTO inventory_changes (hostname, change_type, field, old_value, new_value)
                VALUES (?, 'RENAMED', 'hostname', ?, ?)
                RETURNING id
                """,
                (new_hostname, old_hostname, new_hostname),
            ).fetchone()
            execute(
                connection,
                """
                INSERT INTO host_alias_history
                    (operation_id, host_id, change_id, old_hostname, new_hostname)
                SELECT ?, host_id, ?, ?, ? FROM host_identities WHERE inventory_id=?
                """,
                (operation_id, change["id"], old_hostname, new_hostname, inventory_id),
            )
            execute(
                connection, "UPDATE host_automation_policies SET hostname=? WHERE hostname=?",
                (new_hostname, old_hostname),
            )

    def aliases(self, host_id):
        return self.database.query(
            """
            SELECT old_hostname, new_hostname, recorded_at FROM host_alias_history
            WHERE host_id=? ORDER BY change_id
            """,
            (host_id,),
        )

    def current_host(self, inventory_id, hostname, ip, user, *, include_pending=False):
        rows = self.database.query(
            """
            SELECT host_id, current_incarnation AS incarnation
            FROM host_identities JOIN inventory_hosts ON inventory_id=inventory_hosts.id
            WHERE active=1 AND inventory_hosts.id=? AND hostname=? AND ip=? AND ansible_user=?
              AND (?=1 OR NOT EXISTS (
                  SELECT 1 FROM inventory_endpoint_reviews WHERE inventory_id=inventory_hosts.id
              ))
            """,
            (inventory_id, hostname, ip, user, int(include_pending)),
        )
        return dict(rows[0]) if rows else None

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
            self.database.execute_transaction(
                connection,
                """
                DELETE FROM inventory_endpoint_reviews WHERE inventory_id=(
                    SELECT inventory_id FROM host_identities WHERE host_id=?
                )
                """,
                (host_id,),
            )
            return incarnation

    def confirm_endpoint_move(self, inventory_id):
        return self.database.execute_affected(
            "DELETE FROM inventory_endpoint_reviews WHERE inventory_id=?",
            (inventory_id,),
        ) == 1

    def current(self):
        """Return the active inventory projection in one query."""
        return self.database.query(
            """
            SELECT host_identities.host_id, host_identities.current_incarnation,
                   inventory_hosts.hostname, inventory_hosts.group_name, inventory_hosts.ip,
                   inventory_hosts.ansible_user,
                   EXISTS (
                       SELECT 1 FROM inventory_endpoint_reviews
                       WHERE inventory_endpoint_reviews.inventory_id=inventory_hosts.id
                   ) AS endpoint_review_required
            FROM host_identities
            JOIN inventory_hosts ON inventory_hosts.id=host_identities.inventory_id
            WHERE inventory_hosts.active=1
            ORDER BY inventory_hosts.hostname
            """
        )

    def execution_bindings(self):
        """Capture candidates at dispatch. Ansible verifies connection variables per host."""
        return {
            row["hostname"]: {
                "host_id": row["host_id"],
                "incarnation": row["current_incarnation"],
                "ip": row["ip"],
                "user": row["ansible_user"],
            }
            for row in self.current()
            if row["ip"] and row["ansible_user"] and not row["endpoint_review_required"]
        }

    def identifier(self, inventory_id):
        rows = self.database.query(
            "SELECT host_id FROM host_identities WHERE inventory_id=?", (inventory_id,)
        )
        return rows[0]["host_id"] if rows else None

    def report_bindings(self):
        """Current report identity by hostname, including pending hosts as null."""
        return {
            row["hostname"]: (
                None if row["endpoint_review_required"] else
                {"host_id": row["host_id"], "incarnation": row["current_incarnation"]}
            )
            for row in self.current()
        }

    @staticmethod
    def report_matches(bindings, hostname, identity):
        if hostname not in bindings:
            return identity is None
        return (
            bindings[hostname] is not None
            and isinstance(identity, dict)
            and type(identity.get("incarnation")) is int
            and identity == bindings[hostname]
        )

    def current_hostnames(self):
        """Index verified current incarnations by their stable identity."""
        return {
            (row["host_id"], row["current_incarnation"]): row["hostname"]
            for row in self.current()
            if not row["endpoint_review_required"]
        }

    @staticmethod
    def projected_hostname(current, identity):
        if not isinstance(identity, dict):
            return None
        host_id = identity.get("host_id")
        incarnation = identity.get("incarnation")
        if not isinstance(host_id, str) or type(incarnation) is not int:
            return None
        return current.get((host_id, incarnation))

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
