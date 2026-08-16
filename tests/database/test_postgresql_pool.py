from contextlib import contextmanager
from pathlib import Path

from himp.database.config import DatabaseConfig
from himp.database.postgresql import PostgreSQLDatabase


def postgresql_config():
    return DatabaseConfig(
        backend="postgresql",
        postgres_host="himpdb01.server.arpa",
        postgres_port=5432,
        postgres_database="himp",
        postgres_user="himp_app",
        postgres_password="test-secret",
    )


class FakeCursor:
    def __init__(
        self,
        rows=None,
        row=None,
    ):
        self.calls = []
        self.rows = (
            []
            if rows is None
            else rows
        )
        self.row = row
        self.rowcount = 0
        self.closed = False

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

    def fetchone(self):
        return self.row

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        self.close()
        return False


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
        row=None,
    ):
        self.rows = rows
        self.row = row
        self.cursors = []
        self.transaction_instance = (
            FakeTransaction()
        )

    def cursor(self):
        cursor = FakeCursor(
            rows=self.rows,
            row=self.row,
        )

        self.cursors.append(
            cursor
        )

        return cursor

    def transaction(self):
        return self.transaction_instance

    def execute(
        self,
        sql,
        parameters=(),
    ):
        cursor = self.cursor()

        cursor.execute(
            sql,
            parameters,
        )

        return cursor


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


def database_with_pool(
    pool=None,
):
    database = object.__new__(
        PostgreSQLDatabase
    )

    database.config = postgresql_config()

    database.pool = (
        pool
        if pool is not None
        else FakePool()
    )

    return database


def test_pool_is_bounded():
    assert (
        PostgreSQLDatabase.POOL_MIN_SIZE
        == 1
    )

    assert (
        PostgreSQLDatabase.POOL_MAX_SIZE
        == 8
    )

    assert (
        PostgreSQLDatabase.POOL_TIMEOUT
        == 10
    )


def test_pool_key_is_stable_for_same_configuration():
    first = postgresql_config()
    second = postgresql_config()

    assert (
        PostgreSQLDatabase._pool_key(first)
        == PostgreSQLDatabase._pool_key(second)
    )


def test_query_checks_connection_out_and_back_in():
    connection = FakeConnection(
        rows=[
            {
                "value": 1,
            }
        ]
    )

    pool = FakePool(
        connection=connection
    )

    database = database_with_pool(
        pool
    )

    result = database.query(
        "SELECT ? AS value",
        (
            1,
        ),
    )

    assert result == [
        {
            "value": 1,
        }
    ]

    assert pool.checkouts == 1
    assert pool.returns == 1

    assert (
        connection
        .cursors[0]
        .calls
    ) == [
        (
            "SELECT %s AS value",
            (
                1,
            ),
        )
    ]


def test_transaction_pins_single_connection():
    connection = FakeConnection()

    pool = FakePool(
        connection=connection
    )

    database = database_with_pool(
        pool
    )

    with database.transaction() as borrowed:
        assert borrowed is connection

        database.execute_transaction(
            borrowed,
            "DELETE FROM example WHERE id=?",
            (
                42,
            ),
        )

    assert pool.checkouts == 1
    assert pool.returns == 1

    transaction = (
        connection.transaction_instance
    )

    assert transaction.entries == 1
    assert transaction.exits == 1
    assert transaction.exception_types == [
        None
    ]


def test_connection_context_pins_single_connection():
    connection = FakeConnection()

    pool = FakePool(
        connection=connection
    )

    database = database_with_pool(
        pool
    )

    with database.connection() as borrowed:
        assert borrowed is connection

    assert pool.checkouts == 1
    assert pool.returns == 1


def test_close_does_not_close_shared_pool():
    pool = FakePool()

    database = database_with_pool(
        pool
    )

    result = database.close()

    assert result is None
    assert pool.closed is False


def test_close_pools_closes_each_shared_pool():
    first = FakePool()
    second = FakePool()

    previous = PostgreSQLDatabase._pools

    PostgreSQLDatabase._pools = {
        ("first",): first,
        ("second",): second,
    }

    try:
        PostgreSQLDatabase.close_pools()

        assert first.closed is True
        assert second.closed is True

        assert (
            PostgreSQLDatabase._pools
            == {}
        )

    finally:
        PostgreSQLDatabase._pools = (
            previous
        )


def test_execute_insert_uses_pooled_connection():
    connection = FakeConnection(
        row={
            "id": 363,
        }
    )

    pool = FakePool(
        connection=connection
    )

    database = database_with_pool(
        pool
    )

    identifier = database.execute_insert(
        """
        INSERT INTO inventory_hosts(hostname)
        VALUES (?)
        """,
        (
            "example",
        ),
    )

    assert identifier == 363

    assert pool.checkouts == 1
    assert pool.returns == 1

    sql, parameters = (
        connection
        .cursors[0]
        .calls[0]
    )

    assert "RETURNING id" in sql
    assert "%s" in sql

    assert parameters == (
        "example",
    )

def test_runtime_requirements_include_psycopg_pool():
    requirements = (
        Path("requirements.txt")
        .read_text()
    )

    assert (
        "psycopg[binary,pool]>=3.2"
        in requirements
    )

def test_execute_does_not_leak_cursor_from_pool():
    connection = FakeConnection()

    pool = FakePool(
        connection=connection
    )

    database = database_with_pool(
        pool
    )

    result = database.execute(
        "DELETE FROM example WHERE id=?",
        (
            42,
        ),
    )

    assert result is None

    assert pool.checkouts == 1
    assert pool.returns == 1

    cursor = connection.cursors[0]

    assert cursor.closed is True

    assert cursor.calls == [
        (
            "DELETE FROM example WHERE id=%s",
            (
                42,
            ),
        )
    ]


def test_execute_affected_returns_detached_rowcount():
    connection = FakeConnection()

    pool = FakePool(
        connection=connection
    )

    database = database_with_pool(
        pool
    )

    original_cursor = connection.cursor

    def cursor_with_rowcount():
        cursor = original_cursor()
        cursor.rowcount = 3
        return cursor

    connection.cursor = cursor_with_rowcount

    result = database.execute_affected(
        "DELETE FROM sessions WHERE revoked_at IS NOT NULL"
    )

    assert result == 3
    assert pool.checkouts == 1
    assert pool.returns == 1
    assert connection.cursors[0].closed is True


def test_repository_code_does_not_consume_execute_cursor():
    from pathlib import Path

    consumers = (
        Path("himp/database/sessions.py"),
        Path("himp/database/workflow_executions.py"),
    )

    for path in consumers:
        source = path.read_text()

        assert (
            "cursor = self.database.execute("
            not in source
        )


def test_session_cleanup_uses_affected_row_capability():
    source = Path(
        "himp/database/sessions.py"
    ).read_text()

    assert (
        "self.database.execute_affected("
        in source
    )
