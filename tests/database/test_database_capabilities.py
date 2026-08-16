import sqlite3

import psycopg

from himp.database.config import DatabaseConfig
from himp.database.database import Database
from himp.database.postgresql import PostgreSQLDatabase


class PostgreSQLCapabilityCursor:
    def __init__(
        self,
        row=None,
    ):
        self.calls = []
        self.row = row

    def execute(
        self,
        sql,
        parameters=(),
    ):
        self.calls.append(
            (
                sql,
                parameters,
            )
        )

    def fetchone(self):
        return self.row


class PostgreSQLCapabilityConnection:
    def __init__(
        self,
        row=None,
    ):
        self.cursor_instance = (
            PostgreSQLCapabilityCursor(
                row=row
            )
        )

    def cursor(self):
        return self.cursor_instance


def postgresql_database(
    row=None,
):
    database = object.__new__(
        PostgreSQLDatabase
    )

    database.config = DatabaseConfig(
        backend="postgresql",
        postgres_host="himpdb01.server.arpa",
        postgres_port=5432,
        postgres_database="himp",
        postgres_user="himp_app",
        postgres_password="test-secret",
    )

    database.connection = (
        PostgreSQLCapabilityConnection(
            row=row
        )
    )

    return database


def test_sqlite_table_columns(
    tmp_path,
):
    database = Database(
        config=DatabaseConfig(
            backend="sqlite",
            sqlite_path=(
                tmp_path / "capabilities.db"
            ),
        )
    )

    try:
        database.execute(
            """
            CREATE TABLE capability_test
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
            """
        )

        assert database.table_columns(
            "capability_test"
        ) == {
            "id",
            "name",
        }

    finally:
        database.connection.close()


def test_sqlite_execute_insert_returns_id(
    tmp_path,
):
    database = Database(
        config=DatabaseConfig(
            backend="sqlite",
            sqlite_path=(
                tmp_path / "insert.db"
            ),
        )
    )

    try:
        database.execute(
            """
            CREATE TABLE capability_insert
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
            """
        )

        identifier = database.execute_insert(
            """
            INSERT INTO capability_insert(name)
            VALUES (?)
            """,
            (
                "test",
            ),
        )

        assert identifier == 1

    finally:
        database.connection.close()


def test_sqlite_integrity_error_detection():
    assert Database.is_integrity_error(
        sqlite3.IntegrityError()
    ) is True

    assert Database.is_integrity_error(
        RuntimeError()
    ) is False


def test_postgresql_table_columns():
    database = postgresql_database()

    database.query = lambda sql, parameters=(): [
        {
            "column_name": "id",
        },
        {
            "column_name": "name",
        },
    ]

    assert database.table_columns(
        "example"
    ) == {
        "id",
        "name",
    }


def test_postgresql_execute_insert_adds_returning_id():
    database = postgresql_database(
        row={
            "id": 42,
        }
    )

    identifier = database.execute_insert(
        """
        INSERT INTO example(name)
        VALUES (?)
        """,
        (
            "test",
        ),
    )

    assert identifier == 42

    sql, parameters = (
        database.connection
        .cursor_instance
        .calls[0]
    )

    assert "RETURNING id" in sql
    assert "%s" in sql
    assert parameters == (
        "test",
    )


def test_postgresql_execute_insert_preserves_returning():
    database = postgresql_database(
        row={
            "id": 84,
        }
    )

    identifier = database.execute_insert(
        """
        INSERT INTO example(name)
        VALUES (?)
        RETURNING id
        """,
        (
            "test",
        ),
    )

    assert identifier == 84

    sql = (
        database.connection
        .cursor_instance
        .calls[0][0]
    )

    assert (
        sql.lower().count("returning")
        == 1
    )


def test_postgresql_integrity_error_detection():
    assert (
        PostgreSQLDatabase.is_integrity_error(
            psycopg.IntegrityError()
        )
        is True
    )

    assert (
        PostgreSQLDatabase.is_integrity_error(
            RuntimeError()
        )
        is False
    )


def test_sqlite_lock_transaction_uses_begin_immediate(
    tmp_path,
):
    database = Database(
        config=DatabaseConfig(
            backend="sqlite",
            sqlite_path=(
                tmp_path / "lock.db"
            ),
        )
    )

    calls = []

    class Connection:
        def execute(
            self,
            sql,
        ):
            calls.append(sql)

    try:
        database.begin_lock_transaction(
            Connection()
        )

        assert calls == [
            "BEGIN IMMEDIATE"
        ]

    finally:
        database.connection.close()


def test_postgresql_lock_transaction_is_noop():
    database = postgresql_database()

    assert database.begin_lock_transaction(
        database.connection
    ) is None
