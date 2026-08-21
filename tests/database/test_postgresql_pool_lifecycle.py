from contextlib import contextmanager

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
        postgres_schema="public",
    )


class FakeCursor:
    def __init__(self):
        self.calls = []

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
        return [
            {
                "value": 1,
            }
        ]


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()

    def cursor(self):
        return self.cursor_instance


class FakePool:
    def __init__(self):
        self.closed = False
        self.connection_instance = (
            FakeConnection()
        )
        self.checkouts = 0
        self.returns = 0

    @contextmanager
    def connection(self):
        self.checkouts += 1

        try:
            yield self.connection_instance
        finally:
            self.returns += 1

    def close(self):
        self.closed = True


def test_database_facade_reacquires_pool_after_shutdown(
    monkeypatch,
):
    config = postgresql_config()

    first_pool = FakePool()
    second_pool = FakePool()

    database = object.__new__(
        PostgreSQLDatabase
    )
    database.config = config
    database.pool = first_pool

    calls = []

    def fake_get_pool(
        cls,
        requested_config,
    ):
        assert requested_config is config
        calls.append(
            requested_config
        )
        return second_pool

    monkeypatch.setattr(
        PostgreSQLDatabase,
        "_get_pool",
        classmethod(fake_get_pool),
    )

    first_pool.close()

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

    assert calls == [
        config
    ]

    assert database.pool is second_pool
    assert first_pool.closed is True
    assert first_pool.checkouts == 0

    assert second_pool.closed is False
    assert second_pool.checkouts == 1
    assert second_pool.returns == 1

    assert (
        second_pool
        .connection_instance
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


def test_database_facade_keeps_active_pool(
    monkeypatch,
):
    config = postgresql_config()
    pool = FakePool()

    database = object.__new__(
        PostgreSQLDatabase
    )
    database.config = config
    database.pool = pool

    def unexpected_get_pool(
        cls,
        requested_config,
    ):
        raise AssertionError(
            "active pool should not be reacquired"
        )

    monkeypatch.setattr(
        PostgreSQLDatabase,
        "_get_pool",
        classmethod(
            unexpected_get_pool
        ),
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

    assert database.pool is pool
    assert pool.checkouts == 1
    assert pool.returns == 1
