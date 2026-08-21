import sqlite3
from pathlib import Path

import pytest

from himp.database.migration import (
    IDENTITY_TABLES,
    MIGRATION_TABLES,
    MigrationSchemaError,
    MigrationTargetNotEmptyError,
    SQLitePostgreSQLMigrator,
)


class FakePostgreSQLDatabase:
    def __init__(self):
        self.columns = {}
        self.counts = {}

    def table_columns(self, table):
        return self.columns[table]

    def query(
        self,
        statement,
        parameters=(),
    ):
        normalized = " ".join(
            statement.split()
        )

        if (
            "information_schema.tables"
            in normalized
        ):
            return [
                {
                    "table_name": table,
                }
                for table in MIGRATION_TABLES
            ]

        if "COUNT(*)" in normalized:
            table = normalized.split(
                "FROM ",
                1,
            )[1].split()[0]

            return [
                {
                    "row_count":
                        self.counts.get(
                            table,
                            0,
                        ),
                }
            ]

        raise AssertionError(
            statement
        )


def make_sqlite_database(
    filename,
):
    connection = sqlite3.connect(
        filename
    )

    for table in MIGRATION_TABLES:
        connection.execute(
            f"""
            CREATE TABLE "{table}"
            (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
            """
        )

    connection.commit()
    connection.close()


def make_migrator(
    tmp_path,
):
    filename = (
        tmp_path
        / "source.db"
    )

    make_sqlite_database(
        filename
    )

    database = FakePostgreSQLDatabase()

    for table in MIGRATION_TABLES:
        database.columns[table] = [
            "id",
            "value",
        ]

    migrator = SQLitePostgreSQLMigrator(
        filename,
        database,
    )

    return (
        migrator,
        database,
    )


def test_migration_table_inventory_is_complete():
    assert len(
        MIGRATION_TABLES
    ) == 22

    assert len(
        set(MIGRATION_TABLES)
    ) == 22


def test_identity_table_inventory_is_complete():
    assert len(
        IDENTITY_TABLES
    ) == 19

    assert len(
        set(IDENTITY_TABLES)
    ) == 19

    assert set(
        IDENTITY_TABLES
    ).issubset(
        MIGRATION_TABLES
    )


def test_sqlite_source_opens_read_only(
    tmp_path,
):
    migrator, _ = make_migrator(
        tmp_path
    )

    connection = (
        migrator
        ._open_sqlite_read_only()
    )

    try:
        with pytest.raises(
            sqlite3.OperationalError
        ):
            connection.execute(
                """
                CREATE TABLE forbidden
                (
                    id INTEGER
                )
                """
            )
    finally:
        connection.close()


def test_validate_schema_accepts_matching_tables(
    tmp_path,
):
    migrator, _ = make_migrator(
        tmp_path
    )

    connection = (
        migrator
        ._open_sqlite_read_only()
    )

    try:
        migrator.validate_schema(
            connection
        )
    finally:
        connection.close()


def test_validate_schema_rejects_column_mismatch(
    tmp_path,
):
    migrator, database = (
        make_migrator(
            tmp_path
        )
    )

    database.columns[
        "executions"
    ] = [
        "id",
        "different",
    ]

    connection = (
        migrator
        ._open_sqlite_read_only()
    )

    try:
        with pytest.raises(
            MigrationSchemaError,
            match="Column mismatch",
        ):
            migrator.validate_schema(
                connection
            )
    finally:
        connection.close()


def test_verify_target_empty_accepts_empty_target(
    tmp_path,
):
    migrator, _ = make_migrator(
        tmp_path
    )

    migrator.verify_target_empty()


def test_verify_target_empty_rejects_existing_data(
    tmp_path,
):
    migrator, database = (
        make_migrator(
            tmp_path
        )
    )

    database.counts[
        "inventory_hosts"
    ] = 46

    with pytest.raises(
        MigrationTargetNotEmptyError,
        match="inventory_hosts=46",
    ):
        migrator.verify_target_empty()


def test_source_max_id_preserves_sparse_identity(
    tmp_path,
):
    filename = (
        tmp_path
        / "sparse.db"
    )

    connection = sqlite3.connect(
        filename
    )
    connection.row_factory = sqlite3.Row

    connection.execute(
        """
        CREATE TABLE inventory_hosts
        (
            id INTEGER PRIMARY KEY,
            hostname TEXT
        )
        """
    )

    connection.execute(
        """
        INSERT INTO inventory_hosts
        (
            id,
            hostname
        )
        VALUES
        (
            363,
            'example'
        )
        """
    )

    connection.commit()

    try:
        maximum = (
            SQLitePostgreSQLMigrator
            ._source_max_id(
                connection,
                "inventory_hosts",
            )
        )
    finally:
        connection.close()

    assert maximum == 363


def test_nonidentity_table_has_no_maximum_identity(
    tmp_path,
):
    filename = (
        tmp_path
        / "locks.db"
    )

    connection = sqlite3.connect(
        filename
    )
    connection.row_factory = sqlite3.Row

    connection.execute(
        """
        CREATE TABLE automation_locks
        (
            task_id TEXT PRIMARY KEY
        )
        """
    )

    connection.commit()

    try:
        maximum = (
            SQLitePostgreSQLMigrator
            ._source_max_id(
                connection,
                "automation_locks",
            )
        )
    finally:
        connection.close()

    assert maximum is None


def test_missing_sqlite_source_is_rejected(
    tmp_path,
):
    database = FakePostgreSQLDatabase()

    migrator = SQLitePostgreSQLMigrator(
        tmp_path / "missing.db",
        database,
    )

    with pytest.raises(
        RuntimeError,
        match="does not exist",
    ):
        migrator._open_sqlite_read_only()


class IdentityCursor:
    def __init__(self):
        self.calls = []
        self.fetchone_values = []

    def execute(
        self,
        statement,
        parameters=(),
    ):
        self.calls.append(
            (
                str(statement),
                parameters,
            )
        )

    def fetchone(self):
        return self.fetchone_values.pop(0)


def test_identity_sequence_lookup_requires_sequence():
    cursor = IdentityCursor()
    cursor.fetchone_values = [
        {
            "sequence_name": None,
        }
    ]

    with pytest.raises(
        RuntimeError,
        match="Identity sequence not found",
    ):
        SQLitePostgreSQLMigrator._identity_sequence(
            cursor,
            "inventory_hosts",
        )


def test_identity_sequence_lookup_returns_sequence_name():
    cursor = IdentityCursor()
    cursor.fetchone_values = [
        {
            "sequence_name":
                "public.inventory_hosts_id_seq",
        }
    ]

    result = (
        SQLitePostgreSQLMigrator
        ._identity_sequence(
            cursor,
            "inventory_hosts",
        )
    )

    assert result == (
        "public.inventory_hosts_id_seq"
    )


def test_identity_synchronization_uses_source_maximum():
    cursor = IdentityCursor()
    cursor.fetchone_values = [
        {
            "sequence_name":
                "public.inventory_hosts_id_seq",
        }
    ]

    SQLitePostgreSQLMigrator._synchronize_identity(
        cursor,
        "inventory_hosts",
        363,
    )

    assert len(cursor.calls) == 2

    assert cursor.calls[1][1] == (
        "public.inventory_hosts_id_seq",
        363,
    )


def test_empty_identity_table_does_not_call_setval():
    cursor = IdentityCursor()
    cursor.fetchone_values = [
        {
            "sequence_name":
                "public.workflows_id_seq",
        }
    ]

    SQLitePostgreSQLMigrator._synchronize_identity(
        cursor,
        "workflows",
        None,
    )

    assert len(cursor.calls) == 1


def test_migration_source_and_identity_inventories_are_disjoint_where_expected():
    assert "automation_locks" not in IDENTITY_TABLES
    assert "remediation_operations" not in IDENTITY_TABLES
    assert "users" not in IDENTITY_TABLES

    assert "automation_locks" in MIGRATION_TABLES
    assert "remediation_operations" in MIGRATION_TABLES
    assert "users" in MIGRATION_TABLES
