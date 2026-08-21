from dataclasses import dataclass

import pytest

from himp.services.dependency_impact import (
    DependencyImpactService,
)


@dataclass(frozen=True)
class Relationship:
    source_type: str
    source_id: str
    relationship_type: str
    target_type: str
    target_id: str


class FakeRelationships:
    ENTITY_TYPES = {
        "application",
        "database",
        "host",
        "service",
    }

    def __init__(
        self,
        relationships,
    ):
        self.items = relationships

    def _validate_entity(
        self,
        entity_type,
        entity_id,
    ):
        if (
            not isinstance(entity_type, str)
            or not entity_type.strip()
        ):
            raise ValueError(
                "entity_type must not be empty"
            )

        if (
            not isinstance(entity_id, str)
            or not entity_id.strip()
        ):
            raise ValueError(
                "entity_id must not be empty"
            )

        entity_type = (
            entity_type.strip().lower()
        )

        entity_id = entity_id.strip()

        if entity_type not in self.ENTITY_TYPES:
            raise ValueError(
                "Unsupported entity_type: "
                f"{entity_type}"
            )

        return (
            entity_type,
            entity_id,
        )

    def list_for_source(
        self,
        source_type,
        source_id,
    ):
        return [
            item
            for item in self.items
            if (
                item.source_type
                == source_type
                and item.source_id
                == source_id
            )
        ]

    def list_for_target(
        self,
        target_type,
        target_id,
    ):
        return [
            item
            for item in self.items
            if (
                item.target_type
                == target_type
                and item.target_id
                == target_id
            )
        ]


def production_graph():
    return [
        Relationship(
            source_type="application",
            source_id="himp",
            relationship_type="depends_on",
            target_type="database",
            target_id="himp",
        ),
        Relationship(
            source_type="application",
            source_id="himp",
            relationship_type="runs_on",
            target_type="host",
            target_id="automation.server.arpa",
        ),
        Relationship(
            source_type="database",
            source_id="himp",
            relationship_type="runs_on",
            target_type="host",
            target_id="himpdb01.server.arpa",
        ),
    ]


def service_for(
    relationships=None,
):
    return DependencyImpactService(
        relationships=FakeRelationships(
            relationships
            if relationships is not None
            else production_graph()
        )
    )


def test_dependencies_returns_direct_and_transitive_assets():
    service = service_for()

    result = service.dependencies(
        "application",
        "himp",
    )

    assert result["direction"] == "dependencies"
    assert result["count"] == 3

    assert [
        (
            item["entity_type"],
            item["entity_id"],
            item["depth"],
        )
        for item in result["assets"]
    ] == [
        (
            "database",
            "himp",
            1,
        ),
        (
            "host",
            "automation.server.arpa",
            1,
        ),
        (
            "host",
            "himpdb01.server.arpa",
            2,
        ),
    ]


def test_impact_returns_direct_and_transitive_dependents():
    service = service_for()

    result = service.impact(
        "host",
        "himpdb01.server.arpa",
    )

    assert result["direction"] == "impact"
    assert result["count"] == 2

    assert [
        (
            item["entity_type"],
            item["entity_id"],
            item["depth"],
        )
        for item in result["assets"]
    ] == [
        (
            "database",
            "himp",
            1,
        ),
        (
            "application",
            "himp",
            2,
        ),
    ]


def test_dependencies_include_relationship_path():
    service = service_for()

    result = service.dependencies(
        "application",
        "himp",
    )

    indirect = next(
        item
        for item in result["assets"]
        if (
            item["entity_type"] == "host"
            and item["entity_id"]
            == "himpdb01.server.arpa"
        )
    )

    assert indirect["depth"] == 2
    assert len(indirect["path"]) == 2

    assert (
        indirect["path"][0][
            "relationship_type"
        ]
        == "depends_on"
    )

    assert (
        indirect["path"][1][
            "relationship_type"
        ]
        == "runs_on"
    )


def test_impact_include_relationship_path():
    service = service_for()

    result = service.impact(
        "host",
        "himpdb01.server.arpa",
    )

    application = next(
        item
        for item in result["assets"]
        if item["entity_type"]
        == "application"
    )

    assert application["depth"] == 2
    assert len(application["path"]) == 2

    assert (
        application["path"][0][
            "relationship_type"
        ]
        == "runs_on"
    )

    assert (
        application["path"][1][
            "relationship_type"
        ]
        == "depends_on"
    )


def test_dependencies_honors_max_depth():
    service = service_for()

    result = service.dependencies(
        "application",
        "himp",
        max_depth=1,
    )

    assert result["count"] == 2

    assert all(
        item["depth"] == 1
        for item in result["assets"]
    )


def test_impact_honors_max_depth():
    service = service_for()

    result = service.impact(
        "host",
        "himpdb01.server.arpa",
        max_depth=1,
    )

    assert result["count"] == 1

    assert (
        result["assets"][0]["entity_type"]
        == "database"
    )


@pytest.mark.parametrize(
    "max_depth",
    [
        0,
        -1,
        "2",
        True,
    ],
)
def test_invalid_depth_is_rejected(
    max_depth,
):
    service = service_for()

    with pytest.raises(
        ValueError,
        match=(
            "max_depth must be a "
            "positive integer"
        ),
    ):
        service.dependencies(
            "application",
            "himp",
            max_depth=max_depth,
        )


def test_dependencies_are_cycle_safe():
    relationships = [
        Relationship(
            "application",
            "app",
            "depends_on",
            "service",
            "api",
        ),
        Relationship(
            "service",
            "api",
            "depends_on",
            "database",
            "db",
        ),
        Relationship(
            "database",
            "db",
            "depends_on",
            "application",
            "app",
        ),
    ]

    service = service_for(
        relationships
    )

    result = service.dependencies(
        "application",
        "app",
    )

    assert result["count"] == 2

    assert {
        (
            item["entity_type"],
            item["entity_id"],
        )
        for item in result["assets"]
    } == {
        (
            "service",
            "api",
        ),
        (
            "database",
            "db",
        ),
    }


def test_impact_is_cycle_safe():
    relationships = [
        Relationship(
            "application",
            "app",
            "depends_on",
            "service",
            "api",
        ),
        Relationship(
            "service",
            "api",
            "depends_on",
            "database",
            "db",
        ),
        Relationship(
            "database",
            "db",
            "depends_on",
            "application",
            "app",
        ),
    ]

    service = service_for(
        relationships
    )

    result = service.impact(
        "application",
        "app",
    )

    assert result["count"] == 2


def test_shortest_discovered_path_wins():
    relationships = [
        Relationship(
            "application",
            "app",
            "depends_on",
            "host",
            "shared",
        ),
        Relationship(
            "application",
            "app",
            "depends_on",
            "service",
            "middle",
        ),
        Relationship(
            "service",
            "middle",
            "runs_on",
            "host",
            "shared",
        ),
    ]

    service = service_for(
        relationships
    )

    result = service.dependencies(
        "application",
        "app",
    )

    shared = next(
        item
        for item in result["assets"]
        if item["entity_id"] == "shared"
    )

    assert shared["depth"] == 1
    assert len(shared["path"]) == 1


def test_unknown_entity_type_is_rejected():
    service = service_for()

    with pytest.raises(
        ValueError,
        match="Unsupported entity_type",
    ):
        service.impact(
            "banana",
            "thing",
        )


def test_empty_graph_returns_no_assets():
    service = service_for(
        []
    )

    result = service.dependencies(
        "host",
        "isolated",
    )

    assert result["count"] == 0
    assert result["assets"] == []
