from pathlib import Path

import pytest

from himp.database.config import DatabaseConfig
from himp.database.database import Database


def clear_database_environment(monkeypatch):
    for name in (
        "HIMP_DATABASE_BACKEND",
        "HIMP_DATABASE_PATH",
        "HIMP_DATABASE_HOST",
        "HIMP_DATABASE_PORT",
        "HIMP_DATABASE_NAME",
        "HIMP_DATABASE_USER",
        "HIMP_DATABASE_PASSWORD",
    ):
        monkeypatch.delenv(
            name,
            raising=False,
        )


def test_database_config_defaults_to_sqlite(monkeypatch):
    clear_database_environment(
        monkeypatch
    )

    config = DatabaseConfig.from_environment()

    assert config.backend == "sqlite"
    assert config.is_sqlite is True
    assert config.is_postgresql is False
    assert config.sqlite_path == Path(
        "data/himp.db"
    )
    assert config.postgres_port == 5432


def test_database_config_accepts_custom_sqlite_path(
    monkeypatch,
):
    clear_database_environment(
        monkeypatch
    )

    monkeypatch.setenv(
        "HIMP_DATABASE_PATH",
        "/tmp/himp-test.db",
    )

    config = DatabaseConfig.from_environment()

    assert config.sqlite_path == Path(
        "/tmp/himp-test.db"
    )


def test_database_config_accepts_postgresql(
    monkeypatch,
):
    clear_database_environment(
        monkeypatch
    )

    monkeypatch.setenv(
        "HIMP_DATABASE_BACKEND",
        "postgresql",
    )
    monkeypatch.setenv(
        "HIMP_DATABASE_HOST",
        "himpdb01.server.arpa",
    )
    monkeypatch.setenv(
        "HIMP_DATABASE_PORT",
        "5432",
    )
    monkeypatch.setenv(
        "HIMP_DATABASE_NAME",
        "himp",
    )
    monkeypatch.setenv(
        "HIMP_DATABASE_USER",
        "himp_app",
    )
    monkeypatch.setenv(
        "HIMP_DATABASE_PASSWORD",
        "test-secret",
    )

    config = DatabaseConfig.from_environment()

    assert config.is_postgresql is True
    assert config.is_sqlite is False
    assert (
        config.postgres_host
        == "himpdb01.server.arpa"
    )
    assert config.postgres_port == 5432
    assert config.postgres_database == "himp"
    assert config.postgres_user == "himp_app"
    assert (
        config.postgres_password
        == "test-secret"
    )


def test_database_config_rejects_unknown_backend(
    monkeypatch,
):
    clear_database_environment(
        monkeypatch
    )

    monkeypatch.setenv(
        "HIMP_DATABASE_BACKEND",
        "oracle",
    )

    with pytest.raises(
        ValueError,
        match="Unsupported HIMP database backend",
    ):
        DatabaseConfig.from_environment()


@pytest.mark.parametrize(
    "port",
    (
        "0",
        "65536",
        "not-a-number",
    ),
)
def test_database_config_rejects_invalid_port(
    monkeypatch,
    port,
):
    clear_database_environment(
        monkeypatch
    )

    monkeypatch.setenv(
        "HIMP_DATABASE_PORT",
        port,
    )

    with pytest.raises(
        ValueError,
        match="HIMP_DATABASE_PORT",
    ):
        DatabaseConfig.from_environment()


@pytest.mark.parametrize(
    "missing_name",
    (
        "HIMP_DATABASE_HOST",
        "HIMP_DATABASE_NAME",
        "HIMP_DATABASE_USER",
        "HIMP_DATABASE_PASSWORD",
    ),
)
def test_postgresql_config_requires_all_fields(
    monkeypatch,
    missing_name,
):
    clear_database_environment(
        monkeypatch
    )

    values = {
        "HIMP_DATABASE_BACKEND":
            "postgresql",
        "HIMP_DATABASE_HOST":
            "himpdb01.server.arpa",
        "HIMP_DATABASE_NAME":
            "himp",
        "HIMP_DATABASE_USER":
            "himp_app",
        "HIMP_DATABASE_PASSWORD":
            "test-secret",
    }

    for name, value in values.items():
        monkeypatch.setenv(
            name,
            value,
        )

    monkeypatch.delenv(
        missing_name,
        raising=False,
    )

    with pytest.raises(
        ValueError,
        match="PostgreSQL database configuration "
        "is incomplete",
    ):
        DatabaseConfig.from_environment()

def test_database_uses_default_sqlite_backend(
    monkeypatch,
    tmp_path,
):
    clear_database_environment(
        monkeypatch
    )

    database_path = (
        tmp_path / "default-test.db"
    )

    monkeypatch.setenv(
        "HIMP_DATABASE_PATH",
        str(database_path),
    )

    database = Database()

    try:
        assert database.config.is_sqlite is True
        assert database.filename == database_path
        assert database_path.exists()

        rows = database.query(
            "SELECT 1 AS value"
        )

        assert rows[0]["value"] == 1

    finally:
        database.connection.close()


def test_database_accepts_explicit_sqlite_config(
    tmp_path,
):
    database_path = (
        tmp_path / "explicit-test.db"
    )

    config = DatabaseConfig(
        backend="sqlite",
        sqlite_path=database_path,
    )

    database = Database(
        config=config
    )

    try:
        assert database.config == config
        assert database.filename == database_path
        assert database_path.exists()

    finally:
        database.connection.close()


def test_database_refuses_postgresql_until_backend_exists():
    config = DatabaseConfig(
        backend="postgresql",
        postgres_host="himpdb01.server.arpa",
        postgres_port=5432,
        postgres_database="himp",
        postgres_user="himp_app",
        postgres_password="test-secret",
    )

    config.validate()

    with pytest.raises(
        NotImplementedError,
        match=(
            "PostgreSQL database connections "
            "are not enabled yet"
        ),
    ):
        Database(
            config=config
        )
