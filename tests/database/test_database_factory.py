from pathlib import Path

from himp.database.config import DatabaseConfig
from himp.database.database import Database
from himp.database.factory import create_database
from himp.database.postgresql import PostgreSQLDatabase


def clear_database_environment(
    monkeypatch,
):
    for name in (
        "HIMP_DATABASE_BACKEND",
        "HIMP_DATABASE_PATH",
        "HIMP_DATABASE_HOST",
        "HIMP_DATABASE_PORT",
        "HIMP_DATABASE_NAME",
        "HIMP_DATABASE_USER",
        "HIMP_DATABASE_PASSWORD",
        "HIMP_DATABASE_SCHEMA",
    ):
        monkeypatch.delenv(
            name,
            raising=False,
        )


def test_factory_defaults_to_sqlite(
    monkeypatch,
    tmp_path,
):
    clear_database_environment(
        monkeypatch
    )

    database_path = (
        tmp_path / "factory-default.db"
    )

    monkeypatch.setenv(
        "HIMP_DATABASE_PATH",
        str(database_path),
    )

    database = create_database()

    try:
        assert isinstance(
            database,
            Database,
        )

        assert database.config.is_sqlite
        assert database.filename == database_path
        assert database_path.exists()

    finally:
        database.connection.close()


def test_factory_accepts_explicit_sqlite_config(
    tmp_path,
):
    database_path = (
        tmp_path / "factory-explicit.db"
    )

    config = DatabaseConfig(
        backend="sqlite",
        sqlite_path=database_path,
    )

    database = create_database(
        config=config
    )

    try:
        assert isinstance(
            database,
            Database,
        )

        assert database.config == config
        assert database.filename == database_path

    finally:
        database.connection.close()


def test_factory_selects_postgresql(
    monkeypatch,
):
    config = DatabaseConfig(
        backend="postgresql",
        postgres_host="himpdb01.server.arpa",
        postgres_port=5432,
        postgres_database="himp",
        postgres_user="himp_app",
        postgres_password="test-secret",
    )

    sentinel = object()
    captured = {}

    def fake_postgresql_database(
        config=None,
    ):
        captured["config"] = config
        return sentinel

    monkeypatch.setattr(
        "himp.database.factory.PostgreSQLDatabase",
        fake_postgresql_database,
    )

    database = create_database(
        config=config
    )

    assert database is sentinel
    assert captured["config"] == config


def test_factory_selects_postgresql_from_environment(
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

    sentinel = object()
    captured = {}

    def fake_postgresql_database(
        config=None,
    ):
        captured["config"] = config
        return sentinel

    monkeypatch.setattr(
        "himp.database.factory.PostgreSQLDatabase",
        fake_postgresql_database,
    )

    database = create_database()

    assert database is sentinel

    config = captured["config"]

    assert config.is_postgresql
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


def test_factory_preserves_sqlite_default_without_environment(
    monkeypatch,
    tmp_path,
):
    clear_database_environment(
        monkeypatch
    )

    monkeypatch.chdir(
        tmp_path
    )

    database = create_database()

    try:
        assert isinstance(
            database,
            Database,
        )

        assert database.config.backend == "sqlite"
        assert database.filename == Path(
            "data/himp.db"
        )

    finally:
        database.connection.close()


def test_runtime_database_consumers_use_factory():
    project_root = Path(__file__).resolve().parents[2]

    consumers = (
        "himp/database/inventory.py",
        "himp/database/executions.py",
        "himp/database/health_history.py",
        "himp/database/inventory_baseline.py",
        "himp/database/workflows.py",
        "himp/database/automation_dependencies.py",
        "himp/database/asset_relationships.py",
        "himp/database/automation_executions.py",
        "himp/database/scheduler.py",
        "himp/database/users.py",
        "himp/database/remediation_audit.py",
        "himp/database/sessions.py",
        "himp/database/remediation_operations.py",
        "himp/database/discovery.py",
        "himp/database/workflow_executions.py",
        "himp/database/host_health.py",
        "himp/database/automation_locks.py",
        "himp/services/application_health.py",
    )

    for filename in consumers:
        source = (
            project_root / filename
        ).read_text()

        assert "create_database" in source

        assert (
            "from himp.database.database "
            "import Database"
            not in source
        )

        assert "Database()" not in source


def test_factory_preserves_custom_postgresql_schema(
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
    monkeypatch.setenv(
        "HIMP_DATABASE_SCHEMA",
        "phase_11_6_2_rehearsal",
    )

    sentinel = object()
    captured = {}

    def fake_postgresql_database(
        config=None,
    ):
        captured["config"] = config
        return sentinel

    monkeypatch.setattr(
        "himp.database.factory.PostgreSQLDatabase",
        fake_postgresql_database,
    )

    database = create_database()

    assert database is sentinel

    config = captured["config"]

    assert config.is_postgresql
    assert (
        config.postgres_schema
        == "phase_11_6_2_rehearsal"
    )
