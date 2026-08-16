import pytest

from himp.database.config import DatabaseConfig
from himp.database.postgresql import PostgreSQLDatabase


class FakeCursor:
    def __init__(self):
        self.calls = []
        self.rows = [
            {
                "value": 1,
            }
        ]

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

    def fetchall(self):
        return self.rows


class FakeTransaction:
    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        return False


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
        self.closed = False
        self.transaction_calls = 0

    def cursor(self):
        return self.cursor_instance

    def transaction(self):
        self.transaction_calls += 1
        return FakeTransaction()

    def close(self):
        self.closed = True


def postgresql_config():
    return DatabaseConfig(
        backend="postgresql",
        postgres_host="himpdb01.server.arpa",
        postgres_port=5432,
        postgres_database="himp",
        postgres_user="himp_app",
        postgres_password="test-secret",
    )


def test_postgresql_database_requires_postgresql_config():
    config = DatabaseConfig(
        backend="sqlite",
    )

    with pytest.raises(
        ValueError,
        match=(
            "PostgreSQLDatabase requires "
            "backend=postgresql"
        ),
    ):
        PostgreSQLDatabase(
            config=config
        )


def test_postgresql_sql_placeholder_normalization():
    assert PostgreSQLDatabase._normalize_sql(
        "SELECT * FROM users WHERE username=? AND active=?"
    ) == (
        "SELECT * FROM users "
        "WHERE username=%s AND active=%s"
    )


def test_postgresql_query_uses_normalized_sql():
    database = object.__new__(
        PostgreSQLDatabase
    )

    database.config = postgresql_config()
    database.connection = FakeConnection()

    rows = database.query(
        "SELECT ? AS value",
        (
            1,
        ),
    )

    assert rows == [
        {
            "value": 1,
        }
    ]

    assert (
        database.connection
        .cursor_instance
        .calls
    ) == [
        (
            "SELECT %s AS value",
            (
                1,
            ),
        )
    ]


def test_postgresql_execute_uses_normalized_sql():
    database = object.__new__(
        PostgreSQLDatabase
    )

    database.config = postgresql_config()
    database.connection = FakeConnection()

    database.execute(
        "INSERT INTO example(value) VALUES (?)",
        (
            "test",
        ),
    )

    assert (
        database.connection
        .cursor_instance
        .calls[0]
    ) == (
        "INSERT INTO example(value) VALUES (%s)",
        (
            "test",
        ),
    )


def test_postgresql_transaction_uses_driver_transaction():
    database = object.__new__(
        PostgreSQLDatabase
    )

    database.config = postgresql_config()
    database.connection = FakeConnection()

    with database.transaction() as connection:
        assert connection is database.connection

    assert (
        database.connection.transaction_calls
        == 1
    )


def test_postgresql_close_closes_connection():
    database = object.__new__(
        PostgreSQLDatabase
    )

    database.config = postgresql_config()
    database.connection = FakeConnection()

    database.close()

    assert database.connection.closed is True
