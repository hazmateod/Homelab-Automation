from contextlib import contextmanager

import pytest

from himp.database.config import DatabaseConfig
from himp.database.postgresql import PostgreSQLDatabase


class FakeCursor:
    def __init__(
        self,
        rows=None,
        fail_at=None,
    ):
        self.calls = []
        self.rows = (
            [{"value": 1}]
            if rows is None
            else rows
        )
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
        self.calls.append(
            (
                sql,
                parameters,
            )
        )

        if (
            self.fail_at is not None
            and len(self.calls) == self.fail_at
        ):
            raise RuntimeError(
                "schema initialization failure"
            )

    def fetchall(self):
        return self.rows


class FakeTransaction:
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


class FakeConnection:
    def __init__(
        self,
        rows=None,
        fail_at=None,
    ):
        self.cursor_instance = FakeCursor(
            rows=rows,
            fail_at=fail_at,
        )
        self.transaction_instance = (
            FakeTransaction()
        )

    def cursor(self):
        return self.cursor_instance

    def transaction(self):
        return self.transaction_instance


class FakePool:
    def __init__(
        self,
        connection=None,
    ):
        self.connection_instance = (
            connection
            if connection is not None
            else FakeConnection()
        )
        self.checkouts = 0
        self.returns = 0
        self.closed = False

    @contextmanager
    def connection(self):
        self.checkouts += 1

        try:
            yield self.connection_instance

        finally:
            self.returns += 1

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


def database_with_connection(
    connection=None,
):
    database = object.__new__(
        PostgreSQLDatabase
    )

    database.config = postgresql_config()
    database.pool = FakePool(
        connection=(
            connection
            if connection is not None
            else FakeConnection()
        )
    )

    return database


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
    connection = FakeConnection()

    database = database_with_connection(
        connection
    )

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
        connection.cursor_instance.calls
    ) == [
        (
            "SELECT %s AS value",
            (
                1,
            ),
        )
    ]

    assert database.pool.checkouts == 1
    assert database.pool.returns == 1


def test_postgresql_execute_uses_normalized_sql():
    connection = FakeConnection()

    database = database_with_connection(
        connection
    )

    result = database.execute(
        "INSERT INTO example(value) VALUES (?)",
        (
            "test",
        ),
    )

    assert result is None

    assert (
        connection.cursor_instance.calls[0]
    ) == (
        "INSERT INTO example(value) VALUES (%s)",
        (
            "test",
        ),
    )

    assert database.pool.checkouts == 1
    assert database.pool.returns == 1


def test_postgresql_transaction_uses_driver_transaction():
    connection = FakeConnection()

    database = database_with_connection(
        connection
    )

    with database.transaction() as borrowed:
        assert borrowed is connection

    transaction = (
        connection.transaction_instance
    )

    assert transaction.entries == 1
    assert transaction.exits == 1
    assert transaction.exception_types == [
        None
    ]

    assert database.pool.checkouts == 1
    assert database.pool.returns == 1


def test_postgresql_close_does_not_close_shared_pool():
    database = database_with_connection()

    result = database.close()

    assert result is None
    assert database.pool.closed is False


def test_initialize_schema_executes_every_statement():
    from himp.database.postgresql_schema import (
        schema_statements,
    )

    connection = FakeConnection()

    database = database_with_connection(
        connection
    )

    database.initialize_schema()

    assert [
        sql
        for sql, _parameters
        in connection.cursor_instance.calls
    ] == list(
        schema_statements()
    )

    transaction = (
        connection.transaction_instance
    )

    assert transaction.entries == 1
    assert transaction.exits == 1
    assert transaction.exception_types == [
        None
    ]

    assert (
        connection
        .cursor_instance
        .context_entries
        == 1
    )

    assert (
        connection
        .cursor_instance
        .context_exits
        == 1
    )

    assert database.pool.checkouts == 1
    assert database.pool.returns == 1


def test_initialize_schema_propagates_failure():
    connection = FakeConnection(
        fail_at=5
    )

    database = database_with_connection(
        connection
    )

    with pytest.raises(
        RuntimeError,
        match="schema initialization failure",
    ):
        database.initialize_schema()

    transaction = (
        connection.transaction_instance
    )

    assert transaction.entries == 1
    assert transaction.exits == 1
    assert transaction.exception_types == [
        RuntimeError
    ]

    assert database.pool.checkouts == 1
    assert database.pool.returns == 1


def test_initialize_schema_is_structurally_idempotent():
    from himp.database.postgresql_schema import (
        schema_statements,
    )

    connection = FakeConnection()

    database = database_with_connection(
        connection
    )

    database.initialize_schema()
    database.initialize_schema()

    assert len(
        connection.cursor_instance.calls
    ) == (
        len(schema_statements())
        * 2
    )

    transaction = (
        connection.transaction_instance
    )

    assert transaction.entries == 2
    assert transaction.exits == 2
    assert transaction.exception_types == [
        None,
        None,
    ]

    assert database.pool.checkouts == 2
    assert database.pool.returns == 2


def test_initialize_schema_owns_transaction_boundary():
    connection = FakeConnection()

    database = database_with_connection(
        connection
    )

    database.initialize_schema()

    transaction = (
        connection.transaction_instance
    )

    assert transaction.entries == 1
    assert transaction.exits == 1
    assert transaction.exception_types == [
        None
    ]


def test_initialize_schema_failure_exits_transaction_with_error():
    connection = FakeConnection(
        fail_at=3
    )

    database = database_with_connection(
        connection
    )

    with pytest.raises(
        RuntimeError,
        match="schema initialization failure",
    ):
        database.initialize_schema()

    transaction = (
        connection.transaction_instance
    )

    assert transaction.entries == 1
    assert transaction.exits == 1
    assert transaction.exception_types == [
        RuntimeError
    ]
