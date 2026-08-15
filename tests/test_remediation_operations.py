import pytest

from himp.services.remediation_operations import (
    RemediationOperationsService,
)


class FakeRepository:
    def __init__(
        self,
        configuration=None,
    ):
        self.configuration = configuration
        self.calls = []

    def get(self):
        self.calls.append(
            ("get",)
        )

        return self.configuration

    def save(
        self,
        enabled,
        source_type,
        source_id,
        baseline=None,
        change_limit=10,
    ):
        self.calls.append(
            (
                "save",
                enabled,
                source_type,
                source_id,
                baseline,
                change_limit,
            )
        )

        self.configuration = {
            "enabled": bool(enabled),
            "source_type": source_type,
            "source_id": source_id,
            "baseline": baseline,
            "change_limit": change_limit,
        }

        return self.configuration


def test_get_returns_repository_configuration():
    repository = FakeRepository(
        configuration={
            "enabled": False,
            "source_type": "host",
            "source_id": "pve01",
            "baseline": None,
            "change_limit": 10,
        }
    )

    service = RemediationOperationsService(
        repository=repository
    )

    result = service.get()

    assert result == {
        "enabled": False,
        "source_type": "host",
        "source_id": "pve01",
        "baseline": None,
        "change_limit": 10,
    }

    assert repository.calls == [
        ("get",)
    ]


def test_configure_persists_operational_configuration():
    repository = FakeRepository()

    service = RemediationOperationsService(
        repository=repository
    )

    result = service.configure(
        enabled=True,
        source_type="host",
        source_id="pve01",
        baseline={
            "status": "HEALTHY",
        },
        change_limit=5,
    )

    assert result == {
        "enabled": True,
        "source_type": "host",
        "source_id": "pve01",
        "baseline": {
            "status": "HEALTHY",
        },
        "change_limit": 5,
    }

    assert repository.calls == [
        (
            "save",
            True,
            "host",
            "pve01",
            {
                "status": "HEALTHY",
            },
            5,
        )
    ]


@pytest.mark.parametrize(
    "kwargs, message",
    [
        (
            {
                "enabled": True,
                "source_type": "",
                "source_id": "pve01",
            },
            "source_type is required",
        ),
        (
            {
                "enabled": True,
                "source_type": "host",
                "source_id": "",
            },
            "source_id is required",
        ),
        (
            {
                "enabled": True,
                "source_type": "host",
                "source_id": "pve01",
                "change_limit": 0,
            },
            "change_limit must be at least 1",
        ),
    ],
)
def test_invalid_configuration_is_rejected(
    kwargs,
    message,
):
    service = RemediationOperationsService(
        repository=FakeRepository()
    )

    with pytest.raises(
        ValueError,
        match=message,
    ):
        service.configure(
            **kwargs
        )


class TemporaryDatabase:
    def __init__(self):
        import sqlite3

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


def test_repository_starts_without_configuration():
    from himp.database.remediation_operations import (
        RemediationOperationsRepository,
    )

    database = TemporaryDatabase()

    repository = RemediationOperationsRepository(
        database=database
    )

    assert repository.get() is None


def test_repository_round_trips_configuration():
    from himp.database.remediation_operations import (
        RemediationOperationsRepository,
    )

    database = TemporaryDatabase()

    repository = RemediationOperationsRepository(
        database=database
    )

    result = repository.save(
        enabled=True,
        source_type="host",
        source_id="pve01",
        baseline={
            "status": "HEALTHY",
            "uptime": 42,
        },
        change_limit=7,
    )

    assert result["enabled"] is True
    assert result["source_type"] == "host"
    assert result["source_id"] == "pve01"
    assert result["baseline"] == {
        "status": "HEALTHY",
        "uptime": 42,
    }
    assert result["change_limit"] == 7


def test_repository_updates_single_configuration():
    from himp.database.remediation_operations import (
        RemediationOperationsRepository,
    )

    database = TemporaryDatabase()

    repository = RemediationOperationsRepository(
        database=database
    )

    repository.save(
        enabled=True,
        source_type="host",
        source_id="pve01",
        baseline={
            "status": "HEALTHY",
        },
        change_limit=10,
    )

    result = repository.save(
        enabled=False,
        source_type="host",
        source_id="pve02",
        baseline={
            "status": "WARNING",
        },
        change_limit=3,
    )

    assert result["enabled"] is False
    assert result["source_type"] == "host"
    assert result["source_id"] == "pve02"
    assert result["baseline"] == {
        "status": "WARNING",
    }
    assert result["change_limit"] == 3
