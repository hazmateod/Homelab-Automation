import os
from pathlib import Path

import conftest


ROOT = Path(__file__).resolve().parents[1]


def test_pytest_forces_sqlite_before_test_execution():
    assert (
        os.environ["HIMP_DATABASE_BACKEND"]
        == "sqlite"
    )


def test_pytest_uses_process_local_database():
    database_path = Path(
        os.environ["HIMP_DATABASE_PATH"]
    )

    assert database_path.name.startswith(
        "himp-pytest-"
    )
    assert database_path.suffix == ".db"
    assert str(os.getpid()) in database_path.name


def test_pytest_drops_inherited_postgresql_connection_values():
    for name in (
        "HIMP_DATABASE_HOST",
        "HIMP_DATABASE_PORT",
        "HIMP_DATABASE_NAME",
        "HIMP_DATABASE_USER",
        "HIMP_DATABASE_PASSWORD",
        "HIMP_DATABASE_SCHEMA",
    ):
        assert name not in os.environ


def test_pytest_database_is_not_runtime_database():
    database_path = Path(
        os.environ["HIMP_DATABASE_PATH"]
    ).resolve()

    runtime_database = (
        ROOT / "data/himp.db"
    ).resolve()

    assert database_path != runtime_database


def test_root_conftest_establishes_database_boundary_at_import():
    source = (
        ROOT / "conftest.py"
    ).read_text()

    assert (
        '_force_isolated_test_database()'
        in source
    )
    assert (
        'os.environ["HIMP_DATABASE_BACKEND"] = "sqlite"'
        in source
    )
    assert (
        'os.environ["HIMP_DATABASE_PATH"]'
        in source
    )
