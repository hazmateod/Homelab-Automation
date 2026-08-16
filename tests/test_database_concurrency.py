"""
SQLite database concurrency regression tests.

These tests verify that HIMP serializes access to its shared
SQLite connection and that automation lock acquisition remains
atomic under concurrent execution.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import RLock
import sqlite3
import tempfile

from himp.database.automation_locks import (
    AutomationLockRepository,
)
from himp.database.database import Database


def make_database():
    temporary_directory = tempfile.TemporaryDirectory()

    database = object.__new__(
        Database
    )

    database.path = Path(
        temporary_directory.name
    )

    database.filename = (
        database.path / "himp.db"
    )

    database.connection = sqlite3.connect(
        database.filename,
        check_same_thread=False,
        detect_types=sqlite3.PARSE_DECLTYPES,
    )

    database.connection.row_factory = sqlite3.Row
    database._connection_lock = RLock()

    database.initialize()

    return temporary_directory, database


def make_lock_repository(database):
    repository = object.__new__(
        AutomationLockRepository
    )

    repository.database = database
    repository._ensure_table()

    return repository


def test_concurrent_database_writes_are_serialized():
    temporary_directory, database = make_database()

    try:
        database.execute(
            """
            CREATE TABLE concurrency_test
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker INTEGER NOT NULL,
                sequence INTEGER NOT NULL
            )
            """
        )

        worker_count = 8
        writes_per_worker = 50

        def write_rows(worker):
            for sequence in range(
                writes_per_worker
            ):
                database.execute(
                    """
                    INSERT INTO concurrency_test
                    (
                        worker,
                        sequence
                    )
                    VALUES (?, ?)
                    """,
                    (
                        worker,
                        sequence,
                    ),
                )

        with ThreadPoolExecutor(
            max_workers=worker_count
        ) as executor:
            futures = [
                executor.submit(
                    write_rows,
                    worker,
                )
                for worker in range(
                    worker_count
                )
            ]

            for future in futures:
                future.result()

        rows = database.query(
            """
            SELECT
                worker,
                sequence
            FROM concurrency_test
            ORDER BY
                worker,
                sequence
            """
        )

        assert len(rows) == (
            worker_count
            * writes_per_worker
        )

        for worker in range(
            worker_count
        ):
            worker_rows = [
                row
                for row in rows
                if row["worker"] == worker
            ]

            assert len(worker_rows) == (
                writes_per_worker
            )

            assert [
                row["sequence"]
                for row in worker_rows
            ] == list(
                range(
                    writes_per_worker
                )
            )

    finally:
        database.connection.close()
        temporary_directory.cleanup()


def test_concurrent_queries_and_writes_share_connection_safely():
    temporary_directory, database = make_database()

    try:
        database.execute(
            """
            CREATE TABLE mixed_concurrency_test
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                value INTEGER NOT NULL
            )
            """
        )

        def writer(start):
            for offset in range(40):
                database.execute(
                    """
                    INSERT INTO mixed_concurrency_test
                    (
                        value
                    )
                    VALUES (?)
                    """,
                    (
                        start + offset,
                    ),
                )

        def reader():
            for _ in range(40):
                rows = database.query(
                    """
                    SELECT COUNT(*) AS count
                    FROM mixed_concurrency_test
                    """
                )

                assert rows[0]["count"] >= 0

        with ThreadPoolExecutor(
            max_workers=8
        ) as executor:
            futures = []

            for start in (
                0,
                100,
                200,
                300,
            ):
                futures.append(
                    executor.submit(
                        writer,
                        start,
                    )
                )

            for _ in range(4):
                futures.append(
                    executor.submit(
                        reader
                    )
                )

            for future in futures:
                future.result()

        rows = database.query(
            """
            SELECT COUNT(*) AS count
            FROM mixed_concurrency_test
            """
        )

        assert rows[0]["count"] == 160

    finally:
        database.connection.close()
        temporary_directory.cleanup()


def test_concurrent_lock_acquisition_has_single_winner():
    temporary_directory, database = make_database()

    try:
        repository = make_lock_repository(
            database
        )

        task_id = "concurrent_test_task"

        def acquire_lock():
            return repository.acquire(
                task_id,
                lease_seconds=300,
            )

        with ThreadPoolExecutor(
            max_workers=16
        ) as executor:
            futures = [
                executor.submit(
                    acquire_lock
                )
                for _ in range(16)
            ]

            results = [
                future.result()
                for future in futures
            ]

        assert results.count(True) == 1
        assert results.count(False) == 15

        lock = repository.get(
            task_id
        )

        assert lock is not None
        assert lock["task_id"] == task_id

    finally:
        database.connection.close()
        temporary_directory.cleanup()


def test_lock_can_be_reacquired_after_release():
    temporary_directory, database = make_database()

    try:
        repository = make_lock_repository(
            database
        )

        assert repository.acquire(
            "release_test",
            lease_seconds=300,
        ) is True

        assert repository.acquire(
            "release_test",
            lease_seconds=300,
        ) is False

        repository.release(
            "release_test"
        )

        assert repository.acquire(
            "release_test",
            lease_seconds=300,
        ) is True

    finally:
        database.connection.close()
        temporary_directory.cleanup()
