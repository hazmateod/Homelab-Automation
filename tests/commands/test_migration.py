from himp.commands import migration


class Args:
    execute = False


class ExecuteArgs:
    execute = True


class FakeConfig:
    def __init__(self, postgresql=True):
        self.is_postgresql = postgresql


class FakeDatabase:
    def __init__(self, postgresql=True):
        self.config = FakeConfig(postgresql=postgresql)
        self.close_calls = 0

    def close(self):
        self.close_calls += 1


class FakeTable:
    def __init__(
        self,
        source_rows,
        target_rows,
    ):
        self.source_rows = source_rows
        self.target_rows = target_rows


class FakeResult:
    def __init__(
        self,
        rehearsal,
        tables,
    ):
        self.rehearsal = rehearsal
        self.tables = tuple(tables)

    @property
    def total_rows(self):
        return sum(
            table.source_rows
            for table in self.tables
        )


def test_migration_defaults_to_rehearsal(
    monkeypatch,
):
    database = FakeDatabase()
    calls = []

    def fake_create_database():
        return database

    class FakeMigrator:
        def __init__(
            self,
            sqlite_source,
            postgresql_database,
        ):
            assert (
                sqlite_source
                == migration.SQLITE_SOURCE
            )
            assert (
                postgresql_database
                is database
            )

        @classmethod
        def close_pools(cls):
            pass

        @classmethod
        def close_pools(cls):
            pass

        def migrate(self, *, rehearsal):
            calls.append(rehearsal)
            return FakeResult(
                rehearsal=rehearsal,
                tables=[
                    FakeTable(10, 10),
                ],
            )

    monkeypatch.setattr(
        migration,
        "create_database",
        fake_create_database,
    )
    monkeypatch.setattr(
        migration,
        "SQLitePostgreSQLMigrator",
        FakeMigrator,
    )

    result = migration.run(Args())

    assert result == 0
    assert calls == [True]
    assert database.close_calls == 1


def test_migration_execute_disables_rehearsal(
    monkeypatch,
):
    database = FakeDatabase()
    calls = []

    def fake_create_database():
        return database

    class FakeMigrator:
        def __init__(
            self,
            sqlite_source,
            postgresql_database,
        ):
            pass

        def migrate(self, *, rehearsal):
            calls.append(rehearsal)
            return FakeResult(
                rehearsal=rehearsal,
                tables=[
                    FakeTable(20, 20),
                ],
            )

    monkeypatch.setattr(
        migration,
        "create_database",
        fake_create_database,
    )
    monkeypatch.setattr(
        migration,
        "SQLitePostgreSQLMigrator",
        FakeMigrator,
    )

    result = migration.run(
        ExecuteArgs()
    )

    assert result == 0
    assert calls == [False]
    assert database.close_calls == 1


def test_migration_requires_postgresql(
    monkeypatch,
):
    database = FakeDatabase(
        postgresql=False,
    )

    monkeypatch.setattr(
        migration,
        "create_database",
        lambda: database,
    )

    result = migration.run(Args())

    assert result == 1
    assert database.close_calls == 1


def test_migration_error_returns_failure(
    monkeypatch,
):
    database = FakeDatabase()

    class FakeMigrator:
        def __init__(
            self,
            sqlite_source,
            postgresql_database,
        ):
            pass

        @classmethod
        def close_pools(cls):
            pass

        def migrate(self, *, rehearsal):
            raise migration.MigrationError(
                "controlled migration failure"
            )

    monkeypatch.setattr(
        migration,
        "create_database",
        lambda: database,
    )
    monkeypatch.setattr(
        migration,
        "SQLitePostgreSQLMigrator",
        FakeMigrator,
    )

    result = migration.run(Args())

    assert result == 1
    assert database.close_calls == 1


def test_unexpected_error_returns_failure(
    monkeypatch,
):
    database = FakeDatabase()

    class FakeMigrator:
        def __init__(
            self,
            sqlite_source,
            postgresql_database,
        ):
            pass

        @classmethod
        def close_pools(cls):
            pass

        def migrate(self, *, rehearsal):
            raise RuntimeError(
                "unexpected migration failure"
            )

    monkeypatch.setattr(
        migration,
        "create_database",
        lambda: database,
    )
    monkeypatch.setattr(
        migration,
        "SQLitePostgreSQLMigrator",
        FakeMigrator,
    )

    result = migration.run(Args())

    assert result == 1
    assert database.close_calls == 1


def test_migration_closes_shared_postgresql_pools(
    monkeypatch,
):
    database = FakeDatabase()
    calls = []

    class FakeMigrator:
        def __init__(
            self,
            sqlite_source,
            postgresql_database,
        ):
            pass

        def migrate(self, *, rehearsal):
            return FakeResult(
                rehearsal=rehearsal,
                tables=[
                    FakeTable(1, 1),
                ],
            )

    monkeypatch.setattr(
        migration.PostgreSQLDatabase,
        "close_pools",
        classmethod(
            lambda cls: calls.append(
                "close_pools"
            )
        ),
    )

    monkeypatch.setattr(
        migration,
        "create_database",
        lambda: database,
    )
    monkeypatch.setattr(
        migration,
        "SQLitePostgreSQLMigrator",
        FakeMigrator,
    )

    result = migration.run(Args())

    assert result == 0
    assert database.close_calls == 1
    assert calls == ["close_pools"]
