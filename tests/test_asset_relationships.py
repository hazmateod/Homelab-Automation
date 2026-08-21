import sqlite3

import pytest
import yaml

from himp.database.asset_relationships import (
    AssetRelationshipRepository,
)
from himp.services.asset_relationships import (
    AssetRelationshipService,
)


class TemporaryDatabase:
    def __init__(self):
        self.connection = sqlite3.connect(
            ":memory:"
        )
        self.connection.row_factory = (
            sqlite3.Row
        )

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


def make_repository():
    repository = object.__new__(
        AssetRelationshipRepository
    )
    repository.database = (
        TemporaryDatabase()
    )
    repository.initialize()

    return repository


def make_service(
    config_path=None,
):
    return AssetRelationshipService(
        repository=make_repository(),
        config_path=config_path,
    )


def test_repository_creates_and_lists_relationships():
    repository = make_repository()

    relationship = repository.add(
        source_type="application",
        source_id="himp",
        relationship_type="runs_on",
        target_type="host",
        target_id="automation.server.arpa",
    )

    relationships = repository.list()

    assert relationships == [
        relationship
    ]


def test_repository_prevents_duplicate_relationships():
    repository = make_repository()

    values = {
        "source_type": "application",
        "source_id": "himp",
        "relationship_type": "depends_on",
        "target_type": "database",
        "target_id": "himp",
    }

    repository.add(**values)

    with pytest.raises(
        ValueError,
        match=(
            "Asset relationship already "
            "exists"
        ),
    ):
        repository.add(**values)


def test_repository_lists_relationships_for_source():
    repository = make_repository()

    repository.add(
        "application",
        "himp",
        "runs_on",
        "host",
        "automation.server.arpa",
    )

    repository.add(
        "application",
        "himp",
        "depends_on",
        "database",
        "himp",
    )

    relationships = (
        repository.list_for_source(
            "application",
            "himp",
        )
    )

    assert len(relationships) == 2


def test_repository_lists_relationships_for_target():
    repository = make_repository()

    repository.add(
        "application",
        "himp",
        "runs_on",
        "host",
        "automation.server.arpa",
    )

    relationships = (
        repository.list_for_target(
            "host",
            "automation.server.arpa",
        )
    )

    assert len(relationships) == 1
    assert (
        relationships[0]["source_id"]
        == "himp"
    )


def test_repository_removes_relationship():
    repository = make_repository()

    values = {
        "source_type": "application",
        "source_id": "himp",
        "relationship_type": "depends_on",
        "target_type": "database",
        "target_id": "himp",
    }

    repository.add(**values)
    repository.remove(**values)

    assert repository.list() == []


@pytest.mark.parametrize(
    (
        "field",
        "value",
    ),
    [
        ("source_type", ""),
        ("source_id", ""),
        ("relationship_type", ""),
        ("target_type", ""),
        ("target_id", ""),
    ],
)
def test_service_rejects_empty_values(
    field,
    value,
):
    service = make_service()

    values = {
        "source_type": "application",
        "source_id": "himp",
        "relationship_type": "depends_on",
        "target_type": "database",
        "target_id": "himp",
    }

    values[field] = value

    with pytest.raises(
        ValueError,
        match=field,
    ):
        service.add(**values)


def test_service_rejects_unknown_entity_type():
    service = make_service()

    with pytest.raises(
        ValueError,
        match="Unsupported source_type",
    ):
        service.add(
            "banana",
            "himp",
            "depends_on",
            "database",
            "himp",
        )


def test_service_rejects_unknown_relationship_type():
    service = make_service()

    with pytest.raises(
        ValueError,
        match=(
            "Unsupported relationship_type"
        ),
    ):
        service.add(
            "application",
            "himp",
            "magically_uses",
            "database",
            "himp",
        )


def test_service_rejects_self_relationship():
    service = make_service()

    with pytest.raises(
        ValueError,
        match="cannot target itself",
    ):
        service.add(
            "host",
            "pve01",
            "depends_on",
            "host",
            "pve01",
        )


def test_service_normalizes_contract_values():
    service = make_service()

    relationship = service.add(
        " Application ",
        " himp ",
        " DEPENDS_ON ",
        " Database ",
        " himp ",
    )

    assert (
        relationship.source_type
        == "application"
    )
    assert relationship.source_id == "himp"
    assert (
        relationship.relationship_type
        == "depends_on"
    )
    assert (
        relationship.target_type
        == "database"
    )
    assert relationship.target_id == "himp"


def test_service_lists_models_for_source_and_target():
    service = make_service()

    service.add(
        "application",
        "himp",
        "depends_on",
        "database",
        "himp",
    )

    outgoing = service.list_for_source(
        "application",
        "himp",
    )

    incoming = service.list_for_target(
        "database",
        "himp",
    )

    assert len(outgoing) == 1
    assert len(incoming) == 1

    assert (
        outgoing[0].relationship_type
        == "depends_on"
    )

    assert (
        incoming[0].source_id
        == "himp"
    )


def write_config(
    path,
    relationships,
):
    path.write_text(
        yaml.safe_dump(
            {
                "relationships": (
                    relationships
                )
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_service_loads_desired_relationships(
    tmp_path,
):
    config_path = (
        tmp_path
        / "relationships.yml"
    )

    write_config(
        config_path,
        [
            {
                "source_type": (
                    "application"
                ),
                "source_id": "himp",
                "relationship_type": (
                    "depends_on"
                ),
                "target_type": "database",
                "target_id": "himp",
            }
        ],
    )

    service = make_service(
        config_path=config_path,
    )

    desired = service.load_desired()

    assert len(desired) == 1
    assert desired[0].source_id == "himp"


def test_service_rejects_duplicate_config_relationship(
    tmp_path,
):
    config_path = (
        tmp_path
        / "relationships.yml"
    )

    relationship = {
        "source_type": "application",
        "source_id": "himp",
        "relationship_type": (
            "depends_on"
        ),
        "target_type": "database",
        "target_id": "himp",
    }

    write_config(
        config_path,
        [
            relationship,
            relationship,
        ],
    )

    service = make_service(
        config_path=config_path,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Duplicate infrastructure "
            "relationship"
        ),
    ):
        service.load_desired()


def test_service_reconciles_relationships(
    tmp_path,
):
    config_path = (
        tmp_path
        / "relationships.yml"
    )

    write_config(
        config_path,
        [
            {
                "source_type": (
                    "application"
                ),
                "source_id": "himp",
                "relationship_type": (
                    "depends_on"
                ),
                "target_type": "database",
                "target_id": "himp",
            },
            {
                "source_type": "database",
                "source_id": "himp",
                "relationship_type": (
                    "runs_on"
                ),
                "target_type": "host",
                "target_id": (
                    "himpdb01.server.arpa"
                ),
            },
        ],
    )

    service = make_service(
        config_path=config_path,
    )

    service.add(
        "service",
        "old-service",
        "runs_on",
        "host",
        "old-host",
    )

    result = service.reconcile()

    assert result["configured"] == 2
    assert result["added"] == 2
    assert result["removed"] == 1
    assert result["unchanged"] == 0
    assert result["total"] == 2


def test_service_reconciliation_is_idempotent(
    tmp_path,
):
    config_path = (
        tmp_path
        / "relationships.yml"
    )

    write_config(
        config_path,
        [
            {
                "source_type": (
                    "application"
                ),
                "source_id": "himp",
                "relationship_type": (
                    "depends_on"
                ),
                "target_type": "database",
                "target_id": "himp",
            }
        ],
    )

    service = make_service(
        config_path=config_path,
    )

    first = service.reconcile()
    second = service.reconcile()

    assert first["added"] == 1
    assert first["removed"] == 0

    assert second["added"] == 0
    assert second["removed"] == 0
    assert second["unchanged"] == 1
    assert second["total"] == 1
