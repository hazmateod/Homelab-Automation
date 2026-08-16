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


class SchemaCursor:
    def __init__(
        self,
        fail_at=None,
    ):
        self.executed = []
        self.fail_at = fail_at
        self.context_entries = 0
        self.context_exits = 0

    def __enter__(self):
        self.context_entries += 1
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        self.context_exits += 1
        return False

    def execute(
        self,
        sql,
        parameters=(),
    ):
        self.executed.append(sql)

        if (
            self.fail_at is not None
            and len(self.executed)
            == self.fail_at
        ):
            raise RuntimeError(
                "schema initialization failure"
            )


class SchemaTransaction:
    def __init__(self):
        self.entries = 0
        self.exits = 0
        self.exception_types = []

    def __enter__(self):
        self.entries += 1
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        self.exits += 1
        self.exception_types.append(
            exc_type
        )
        return False


class SchemaConnection:
    def __init__(
        self,
        fail_at=None,
    ):
        self.cursor_instance = SchemaCursor(
            fail_at=fail_at
        )
        self.transaction_instance = (
            SchemaTransaction()
        )

    def cursor(self):
        return self.cursor_instance

    def transaction(self):
        return self.transaction_instance


def test_initialize_schema_executes_every_statement():
    from himp.database.postgresql_schema import (
        schema_statements,
    )

    database = object.__new__(
        PostgreSQLDatabase
    )

    database.config = postgresql_config()
    database.connection = SchemaConnection()

    database.initialize_schema()

    assert (
        database.connection
        .cursor_instance
        .executed
    ) == list(
        schema_statements()
    )

    assert (
        database.connection
        .transaction_instance
        .entries
        == 1
    )

    assert (
        database.connection
        .transaction_instance
        .exits
        == 1
    )

    assert (
        database.connection
        .cursor_instance
        .context_entries
        == 1
    )

    assert (
        database.connection
        .cursor_instance
        .context_exits
        == 1
    )


def test_initialize_schema_propagates_failure():
    database = object.__new__(
        PostgreSQLDatabase
    )

    database.config = postgresql_config()
    database.connection = SchemaConnection(
        fail_at=5
    )

    with pytest.raises(
        RuntimeError,
        match="schema initialization failure",
    ):
        database.initialize_schema()

    transaction = (
        database.connection
        .transaction_instance
    )

    assert transaction.entries == 1
    assert transaction.exits == 1
    assert transaction.exception_types == [
        RuntimeError
    ]


def test_initialize_schema_is_structurally_idempotent():
    database = object.__new__(
        PostgreSQLDatabase
    )

    database.config = postgresql_config()
    database.connection = SchemaConnection()

    database.initialize_schema()
    database.initialize_schema()

    from himp.database.postgresql_schema import (
        schema_statements,
    )

    assert len(
        database.connection
        .cursor_instance
        .executed
    ) == (
        len(schema_statements())
        * 2
    )

    assert (
        database.connection
        .transaction_instance
        .entries
        == 2
    )

    assert (
        database.connection
        .transaction_instance
        .exits
        == 2
    )

def test_initialize_schema_owns_transaction_boundary():
    database = object.__new__(
        PostgreSQLDatabase
    )

    database.config = postgresql_config()
    database.connection = SchemaConnection()

    database.initialize_schema()

    transaction = (
        database.connection
        .transaction_instance
    )

    assert transaction.entries == 1
    assert transaction.exits == 1
    assert transaction.exception_types == [
        None
    ]


def test_initialize_schema_failure_exits_transaction_with_error():
    database = object.__new__(
        PostgreSQLDatabase
    )

    database.config = postgresql_config()
    database.connection = SchemaConnection(
        fail_at=3
    )

    with pytest.raises(
        RuntimeError,
        match="schema initialization failure",
    ):
        database.initialize_schema()

    transaction = (
        database.connection
        .transaction_instance
    )

    assert transaction.entries == 1
    assert transaction.exits == 1
    assert transaction.exception_types == [
        RuntimeError
    ]
