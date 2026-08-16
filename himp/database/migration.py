"""
SQLite to PostgreSQL migration support for HIMP.

The migration service preserves existing primary-key values and
application data while moving a complete HIMP database from SQLite
to PostgreSQL.

Safety properties:

* SQLite is opened read-only.
* PostgreSQL must already contain the HIMP schema.
* PostgreSQL target tables must be empty before migration.
* Source and target schemas are validated before copying.
* All PostgreSQL writes occur inside one transaction.
* Explicit SQLite identity values are preserved.
* PostgreSQL identity sequences are synchronized to migrated IDs.
* Row counts are verified before the transaction may commit.
* Rehearsal mode deliberately rolls the transaction back.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from psycopg import sql


MIGRATION_TABLES = (
    "executions",
    "health_history",
    "inventory_hosts",
    "inventory_changes",
    "inventory_baselines",
    "workflows",
    "workflow_tasks",
    "workflow_dependencies",
    "workflow_executions",
    "automation_dependencies",
    "asset_relationships",
    "automation_executions",
    "automation_locks",
    "automation_schedules",
    "remediation_audit",
    "remediation_operations",
    "sessions",
    "users",
    "discovery",
    "host_health_history",
)


IDENTITY_TABLES = (
    "asset_relationships",
    "automation_dependencies",
    "automation_executions",
    "automation_schedules",
    "discovery",
    "executions",
    "health_history",
    "host_health_history",
    "inventory_baselines",
    "inventory_changes",
    "inventory_hosts",
    "remediation_audit",
    "sessions",
    "workflow_dependencies",
    "workflow_executions",
    "workflow_tasks",
    "workflows",
)


class MigrationError(RuntimeError):
    """Base migration failure."""


class MigrationSchemaError(MigrationError):
    """Source and target schemas are incompatible."""


class MigrationTargetNotEmptyError(MigrationError):
    """PostgreSQL contains data and cannot be safely migrated."""


class MigrationVerificationError(MigrationError):
    """Migrated data failed verification."""


class MigrationRehearsalRollback(Exception):
    """
    Internal exception used to force PostgreSQL transaction rollback
    after a successful rehearsal.
    """


@dataclass(frozen=True)
class TableMigrationResult:
    table: str
    source_rows: int
    target_rows: int
    source_max_id: int | None = None


@dataclass(frozen=True)
class MigrationResult:
    rehearsal: bool
    tables: tuple[TableMigrationResult, ...]

    @property
    def total_rows(self):
        return sum(
            table.source_rows
            for table in self.tables
        )


class SQLitePostgreSQLMigrator:
    def __init__(
        self,
        sqlite_filename,
        postgresql_database,
    ):
        self.sqlite_filename = Path(
            sqlite_filename
        ).resolve()

        self.postgresql_database = (
            postgresql_database
        )

    def _open_sqlite_read_only(self):
        if not self.sqlite_filename.is_file():
            raise MigrationError(
                "SQLite source database does not exist: "
                f"{self.sqlite_filename}"
            )

        uri = (
            "file:"
            + quote(
                str(self.sqlite_filename),
                safe="/",
            )
            + "?mode=ro"
        )

        connection = sqlite3.connect(
            uri,
            uri=True,
        )
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _sqlite_tables(connection):
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        return {
            row["name"]
            for row in rows
        }

    @staticmethod
    def _sqlite_columns(
        connection,
        table,
    ):
        rows = connection.execute(
            f'PRAGMA table_info("{table}")'
        ).fetchall()

        return tuple(
            row["name"]
            for row in rows
        )

    def _postgresql_tables(self):
        rows = self.postgresql_database.query(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = current_schema()
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )

        return {
            row["table_name"]
            for row in rows
        }

    def validate_schema(
        self,
        sqlite_connection,
    ):
        source_tables = self._sqlite_tables(
            sqlite_connection
        )
        target_tables = (
            self._postgresql_tables()
        )

        expected = set(
            MIGRATION_TABLES
        )

        missing_source = (
            expected - source_tables
        )
        missing_target = (
            expected - target_tables
        )

        if missing_source:
            raise MigrationSchemaError(
                "SQLite source is missing tables: "
                + ", ".join(
                    sorted(missing_source)
                )
            )

        if missing_target:
            raise MigrationSchemaError(
                "PostgreSQL target is missing tables: "
                + ", ".join(
                    sorted(missing_target)
                )
            )

        for table in MIGRATION_TABLES:
            source_columns = set(
                self._sqlite_columns(
                    sqlite_connection,
                    table,
                )
            )

            target_columns = set(
                self.postgresql_database
                .table_columns(table)
            )

            if source_columns != target_columns:
                raise MigrationSchemaError(
                    f"Column mismatch for {table}: "
                    f"source={sorted(source_columns)} "
                    f"target={sorted(target_columns)}"
                )

    def verify_target_empty(self):
        nonempty = {}

        for table in MIGRATION_TABLES:
            rows = self.postgresql_database.query(
                f"""
                SELECT COUNT(*) AS row_count
                FROM {table}
                """
            )

            count = rows[0]["row_count"]

            if count:
                nonempty[table] = count

        if nonempty:
            details = ", ".join(
                f"{table}={count}"
                for table, count
                in sorted(nonempty.items())
            )

            raise MigrationTargetNotEmptyError(
                "PostgreSQL migration target "
                "is not empty: "
                + details
            )

    @staticmethod
    def _source_rows(
        sqlite_connection,
        table,
    ):
        return sqlite_connection.execute(
            f'SELECT * FROM "{table}"'
        ).fetchall()

    @staticmethod
    def _source_max_id(
        sqlite_connection,
        table,
    ):
        if table not in IDENTITY_TABLES:
            return None

        row = sqlite_connection.execute(
            f'SELECT MAX(id) AS max_id '
            f'FROM "{table}"'
        ).fetchone()

        return row["max_id"]

    @staticmethod
    def _insert_rows(
        cursor,
        table,
        rows,
    ):
        if not rows:
            return

        columns = tuple(
            rows[0].keys()
        )

        statement = sql.SQL(
            "INSERT INTO {} ({}) VALUES ({})"
        ).format(
            sql.Identifier(table),
            sql.SQL(", ").join(
                sql.Identifier(column)
                for column in columns
            ),
            sql.SQL(", ").join(
                sql.Placeholder()
                for _ in columns
            ),
        )

        for row in rows:
            cursor.execute(
                statement,
                tuple(
                    row[column]
                    for column in columns
                ),
            )

    @staticmethod
    def _target_count(
        cursor,
        table,
    ):
        cursor.execute(
            sql.SQL(
                "SELECT COUNT(*) AS row_count FROM {}"
            ).format(
                sql.Identifier(table)
            )
        )

        return cursor.fetchone()["row_count"]

    @staticmethod
    def _identity_sequence(
        cursor,
        table,
    ):
        cursor.execute(
            """
            SELECT pg_get_serial_sequence(
                %s,
                'id'
            ) AS sequence_name
            """,
            (
                table,
            ),
        )

        sequence_name = (
            cursor.fetchone()["sequence_name"]
        )

        if not sequence_name:
            raise MigrationVerificationError(
                "Identity sequence not found for "
                f"{table}.id"
            )

        return sequence_name

    @classmethod
    def _synchronize_identity(
        cls,
        cursor,
        table,
        maximum_id,
    ):
        sequence_name = cls._identity_sequence(
            cursor,
            table,
        )

        if maximum_id is None:
            return

        cursor.execute(
            """
            SELECT setval(
                %s::regclass,
                %s,
                true
            )
            """,
            (
                sequence_name,
                maximum_id,
            ),
        )

    def migrate(
        self,
        *,
        rehearsal=True,
    ):
        sqlite_connection = (
            self._open_sqlite_read_only()
        )

        results = []

        try:
            self.validate_schema(
                sqlite_connection
            )
            self.verify_target_empty()

            try:
                with (
                    self.postgresql_database
                    .connection
                    .transaction()
                ):
                    with (
                        self.postgresql_database
                        .connection
                        .cursor()
                    ) as cursor:
                        for table in MIGRATION_TABLES:
                            rows = self._source_rows(
                                sqlite_connection,
                                table,
                            )

                            source_count = len(rows)

                            self._insert_rows(
                                cursor,
                                table,
                                rows,
                            )

                            target_count = (
                                self._target_count(
                                    cursor,
                                    table,
                                )
                            )

                            if (
                                source_count
                                != target_count
                            ):
                                raise (
                                    MigrationVerificationError(
                                        "Row count mismatch "
                                        f"for {table}: "
                                        f"source={source_count} "
                                        f"target={target_count}"
                                    )
                                )

                            maximum_id = (
                                self._source_max_id(
                                    sqlite_connection,
                                    table,
                                )
                            )

                            if table in IDENTITY_TABLES:
                                # Confirm the identity sequence exists
                                # during both rehearsal and migration.
                                # Sequence setval() operations are not
                                # transactionally reversible, so rehearsal
                                # must never alter sequence state.
                                self._identity_sequence(
                                    cursor,
                                    table,
                                )

                            results.append(
                                TableMigrationResult(
                                    table=table,
                                    source_rows=source_count,
                                    target_rows=target_count,
                                    source_max_id=maximum_id,
                                )
                            )

                    if rehearsal:
                        raise (
                            MigrationRehearsalRollback()
                        )

                    # Synchronize identity sequences only after every
                    # table has been copied and row-count verified.
                    # Rehearsal never executes setval().
                    with (
                        self.postgresql_database
                        .connection
                        .cursor()
                    ) as identity_cursor:
                        for result in results:
                            if (
                                result.table
                                not in IDENTITY_TABLES
                            ):
                                continue

                            self._synchronize_identity(
                                identity_cursor,
                                result.table,
                                result.source_max_id,
                            )

            except MigrationRehearsalRollback:
                pass

        finally:
            sqlite_connection.close()

        return MigrationResult(
            rehearsal=rehearsal,
            tables=tuple(results),
        )
