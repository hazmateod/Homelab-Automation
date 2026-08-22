"""
Global pytest safety boundary.

HIMP production uses environment-selected PostgreSQL persistence.
A developer or operator shell may legitimately have /etc/himp/database.env
exported while running repository tests.

Never allow ordinary pytest collection/execution to inherit that production
database target. Force the test process onto an isolated SQLite database
before test modules are imported.

Tests that explicitly exercise DatabaseConfig/PostgreSQL selection may
override these values locally with pytest's monkeypatch fixture.
"""

import atexit
import os
from pathlib import Path
import tempfile


_TEST_DATABASE = (
    Path(tempfile.gettempdir())
    / f"himp-pytest-{os.getpid()}.db"
)


def _force_isolated_test_database():
    """
    Establish pytest's database boundary before test-module import.
    """
    os.environ["HIMP_DATABASE_BACKEND"] = "sqlite"
    os.environ["HIMP_DATABASE_PATH"] = str(
        _TEST_DATABASE
    )

    # Production PostgreSQL connection values are deliberately
    # removed from the pytest process. Tests that need to exercise
    # PostgreSQL configuration set their own synthetic values.
    for name in (
        "HIMP_DATABASE_HOST",
        "HIMP_DATABASE_PORT",
        "HIMP_DATABASE_NAME",
        "HIMP_DATABASE_USER",
        "HIMP_DATABASE_PASSWORD",
        "HIMP_DATABASE_SCHEMA",
    ):
        os.environ.pop(name, None)


def _remove_test_database():
    """
    Remove pytest's process-local SQLite database after the run.
    """
    try:
        _TEST_DATABASE.unlink()
    except FileNotFoundError:
        pass

    for suffix in (
        "-journal",
        "-shm",
        "-wal",
    ):
        try:
            Path(
                str(_TEST_DATABASE) + suffix
            ).unlink()
        except FileNotFoundError:
            pass


_force_isolated_test_database()
atexit.register(_remove_test_database)
