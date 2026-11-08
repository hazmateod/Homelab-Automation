from contextlib import contextmanager
import sqlite3
from datetime import datetime, timedelta

from himp.database.automation_locks import (
    AutomationLockRepository,
)


class TemporaryDatabase:
    def __init__(self):
        self.connection = sqlite3.connect(
            ":memory:"
        )
        self.connection.row_factory = sqlite3.Row

    def execute(
        self,
        sql,
        parameters=(),
    ):
        cursor = self.connection.cursor()
        cursor.execute(
            sql,
            parameters,
        )
        self.connection.commit()
        return cursor

    def query(
        self,
        sql,
        parameters=(),
    ):
        cursor = self.connection.cursor()
        cursor.execute(
            sql,
            parameters,
        )
        return cursor.fetchall()

    def table_columns(self, table_name):
        cursor = self.connection.execute(
            f"PRAGMA table_info({table_name})"
        )
        return [row["name"] for row in cursor.fetchall()]

    def execute_affected(self, sql, parameters=()):
        cursor = self.execute(sql, parameters)
        return cursor.rowcount

    def begin_lock_transaction(self, connection):
        connection.execute("BEGIN IMMEDIATE")

    def execute_transaction(
        self,
        connection,
        sql,
        parameters=(),
    ):
        return connection.execute(
            sql,
            parameters,
        )

    @contextmanager
    def transaction(self):
        try:
            yield self.connection
            self.connection.commit()

        except Exception:
            self.connection.rollback()
            raise


def make_repository():
    repository = object.__new__(
        AutomationLockRepository
    )

    repository.database = TemporaryDatabase()

    repository._ensure_table()

    return repository


def test_first_acquire_succeeds():
    repository = make_repository()

    assert repository.acquire(
        "health_check", execution_token="test-execution-1"
    ) is True

    lock = repository.get(
        "health_check"
    )

    assert lock is not None
    assert lock["task_id"] == "health_check"


def test_second_acquire_for_same_task_fails():
    repository = make_repository()

    assert repository.acquire(
        "health_check", execution_token="test-execution-2"
    ) is True

    assert repository.acquire(
        "health_check", execution_token="test-execution-3"
    ) is False


def test_different_tasks_can_acquire_independently():
    repository = make_repository()

    assert repository.acquire(
        "health_check", execution_token="test-execution-4"
    ) is True

    assert repository.acquire(
        "generate_reports", execution_token="test-execution-5"
    ) is True

    assert repository.get(
        "health_check"
    ) is not None

    assert repository.get(
        "generate_reports"
    ) is not None


def test_release_allows_subsequent_acquire():
    repository = make_repository()

    assert repository.acquire(
        "health_check", execution_token="test-execution-6"
    ) is True

    repository.release(
        "health_check",
        execution_token="test-execution-6",
    )

    assert repository.get(
        "health_check"
    ) is None

    assert repository.acquire(
        "health_check", execution_token="test-execution-7"
    ) is True


def test_expired_lease_can_be_reclaimed():
    repository = make_repository()

    assert repository.acquire(
        "health_check", execution_token="test-execution-8",
        lease_seconds=-1,
    ) is True

    lock = repository.get(
        "health_check"
    )

    assert lock is not None

    assert repository.acquire(
        "health_check", execution_token="test-execution-9"
    ) is True

    refreshed = repository.get(
        "health_check"
    )

    assert refreshed is not None

    assert (
        refreshed["expires_at"]
        > refreshed["locked_at"]
    )
