import sqlite3

import pytest

from himp.database.asset_relationships import (
    AssetRelationshipRepository,
)


class TemporaryDatabase:
    def __init__(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row

    def execute(self, sql, parameters=()):
        cursor = self.connection.cursor()
        cursor.execute(sql, parameters)
        self.connection.commit()
        return cursor

    def query(self, sql, parameters=()):
        cursor = self.connection.cursor()
        cursor.execute(sql, parameters)
        return cursor.fetchall()


def make_repository():
    repository = object.__new__(
        AssetRelationshipRepository
    )
    repository.database = TemporaryDatabase()
    repository.initialize()
    return repository
from himp.services.asset_relationships import (
    AssetRelationshipService,
)


class TemporaryDatabase:
    def __init__(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row

    def execute(self, sql, parameters=()):
        cursor = self.connection.cursor()
        cursor.execute(sql, parameters)
        self.connection.commit()
        return cursor

    def query(self, sql, parameters=()):
        cursor = self.connection.cursor()
        cursor.execute(sql, parameters)
        return cursor.fetchall()


def make_repository():
    repository = object.__new__(
        AssetRelationshipRepository
    )
    repository.database = TemporaryDatabase()
    repository.initialize()
    return repository


def test_repository_creates_and_lists_relationships():
    repository = make_repository()

    relationship = repository.add(
        source_type="host",
        source_id="pve01",
        relationship_type="runs",
        target_type="service",
        target_id="pbs",
    )

    assert relationship["source_type"] == "host"
    assert relationship["source_id"] == "pve01"
    assert relationship["relationship_type"] == "runs"
    assert relationship["target_type"] == "service"
    assert relationship["target_id"] == "pbs"

    relationships = repository.list()

    assert relationships == [relationship]


def test_repository_prevents_duplicate_relationships():
    repository = make_repository()

    repository.add(
        source_type="host",
        source_id="pve01",
        relationship_type="runs",
        target_type="service",
        target_id="pbs",
    )

    with pytest.raises(
        ValueError,
        match="Asset relationship already exists",
    ):
        repository.add(
            source_type="host",
            source_id="pve01",
            relationship_type="runs",
            target_type="service",
            target_id="pbs",
        )


def test_repository_lists_relationships_for_source():
    repository = make_repository()

    first = repository.add(
        source_type="host",
        source_id="pve01",
        relationship_type="runs",
        target_type="service",
        target_id="pbs",
    )

    repository.add(
        source_type="host",
        source_id="pve01",
        relationship_type="hosts",
        target_type="vm",
        target_id="vm100",
    )

    repository.add(
        source_type="host",
        source_id="pve02",
        relationship_type="runs",
        target_type="service",
        target_id="dns",
    )

    relationships = repository.list_for_source(
        source_type="host",
        source_id="pve01",
    )

    assert len(relationships) == 2
    assert relationships[0] == first
    assert relationships[1]["source_type"] == "host"
    assert relationships[1]["source_id"] == "pve01"
    assert relationships[1]["relationship_type"] == "hosts"
    assert relationships[1]["target_type"] == "vm"
    assert relationships[1]["target_id"] == "vm100"


def test_service_validates_relationship_values():
    repository = make_repository()
    service = AssetRelationshipService(
        repository=repository,
    )

    with pytest.raises(ValueError, match="source_type"):
        service.add(
            source_type="",
            source_id="pve01",
            relationship_type="runs",
            target_type="service",
            target_id="pbs",
        )

    with pytest.raises(ValueError, match="source_id"):
        service.add(
            source_type="host",
            source_id="",
            relationship_type="runs",
            target_type="service",
            target_id="pbs",
        )

    with pytest.raises(ValueError, match="relationship_type"):
        service.add(
            source_type="host",
            source_id="pve01",
            relationship_type="",
            target_type="service",
            target_id="pbs",
        )

    with pytest.raises(ValueError, match="target_type"):
        service.add(
            source_type="host",
            source_id="pve01",
            relationship_type="runs",
            target_type="",
            target_id="pbs",
        )

    with pytest.raises(ValueError, match="target_id"):
        service.add(
            source_type="host",
            source_id="pve01",
            relationship_type="runs",
            target_type="service",
            target_id="",
        )


def test_service_lists_asset_relationship_models():
    class FakeRepository:
        def list(self):
            return [
                {
                    "source_type": "host",
                    "source_id": "pve01",
                    "relationship_type": "runs",
                    "target_type": "service",
                    "target_id": "pbs",
                },
            ]

    service = AssetRelationshipService(
        repository=FakeRepository()
    )

    relationships = service.list()

    assert len(relationships) == 1
    assert relationships[0].source_type == "host"
    assert relationships[0].source_id == "pve01"
    assert relationships[0].relationship_type == "runs"
    assert relationships[0].target_type == "service"
    assert relationships[0].target_id == "pbs"


def test_service_lists_relationships_for_source():
    class FakeRepository:
        def list_for_source(
            self,
            source_type,
            source_id,
        ):
            assert source_type == "host"
            assert source_id == "pve01"

            return [
                {
                    "source_type": "host",
                    "source_id": "pve01",
                    "relationship_type": "runs",
                    "target_type": "service",
                    "target_id": "pbs",
                },
            ]

    service = AssetRelationshipService(
        repository=FakeRepository()
    )

    relationships = service.list_for_source(
        source_type="host",
        source_id="pve01",
    )

    assert len(relationships) == 1
    assert relationships[0].source_type == "host"
    assert relationships[0].source_id == "pve01"
    assert relationships[0].relationship_type == "runs"
    assert relationships[0].target_type == "service"
    assert relationships[0].target_id == "pbs"


def test_repository_lists_relationships_for_target():
    repository = make_repository()

    first = repository.add(
        source_type="host",
        source_id="pve01",
        relationship_type="runs",
        target_type="service",
        target_id="pbs",
    )

    repository.add(
        source_type="host",
        source_id="pve02",
        relationship_type="runs",
        target_type="service",
        target_id="pbs",
    )

    repository.add(
        source_type="host",
        source_id="pve01",
        relationship_type="hosts",
        target_type="vm",
        target_id="vm100",
    )

    relationships = repository.list_for_target(
        target_type="service",
        target_id="pbs",
    )

    assert len(relationships) == 2
    assert relationships[0] == first
    assert relationships[1]["source_type"] == "host"
    assert relationships[1]["source_id"] == "pve02"
    assert relationships[1]["relationship_type"] == "runs"
    assert relationships[1]["target_type"] == "service"
    assert relationships[1]["target_id"] == "pbs"


def test_service_lists_relationships_for_target():
    class FakeRepository:
        def list_for_target(
            self,
            target_type,
            target_id,
        ):
            assert target_type == "service"
            assert target_id == "pbs"

            return [
                {
                    "source_type": "host",
                    "source_id": "pve01",
                    "relationship_type": "runs",
                    "target_type": "service",
                    "target_id": "pbs",
                },
            ]

    service = AssetRelationshipService(
        repository=FakeRepository()
    )

    relationships = service.list_for_target(
        target_type="service",
        target_id="pbs",
    )

    assert len(relationships) == 1
    assert relationships[0].source_type == "host"
    assert relationships[0].source_id == "pve01"
    assert relationships[0].relationship_type == "runs"
    assert relationships[0].target_type == "service"
    assert relationships[0].target_id == "pbs"
