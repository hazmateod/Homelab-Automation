from dataclasses import dataclass

from himp.services.continuity_impact import (
    ContinuityImpactService,
)


@dataclass(frozen=True)
class Relationship:
    source_type: str
    source_id: str
    relationship_type: str
    target_type: str
    target_id: str


class FakeDependencies:
    def __init__(
        self,
        result,
    ):
        self.result = result
        self.last_max_depth = None

    def impact(
        self,
        entity_type,
        entity_id,
        max_depth=None,
    ):
        self.last_max_depth = max_depth

        result = dict(
            self.result
        )

        result["entity_type"] = entity_type
        result["entity_id"] = entity_id
        result["max_depth"] = max_depth

        return result


class FakeMetadata:
    def __init__(
        self,
        entries,
    ):
        self.entries = entries

    def get(
        self,
        entity_type,
        entity_id,
    ):
        return self.entries.get(
            (
                entity_type,
                entity_id,
            )
        )


def metadata(
    display_name,
    criticality="important",
):
    return {
        "entity_type": "service",
        "entity_id": display_name.lower(),
        "display_name": display_name,
        "continuity_role": "test",
        "criticality": criticality,
        "household_impact": (
            f"{display_name} may be affected."
        ),
        "recovery_authority": "technical_only",
        "can_wait": "Wait for technical help.",
    }


def impact_graph(
    assets=None,
):
    assets = (
        assets
        if assets is not None
        else []
    )

    return {
        "entity_type": "host",
        "entity_id": "server",
        "direction": "impact",
        "count": len(assets),
        "max_depth": None,
        "assets": assets,
    }


def test_root_metadata_is_included():
    root = metadata(
        "Server",
        "important",
    )

    service = ContinuityImpactService(
        dependencies=FakeDependencies(
            impact_graph()
        ),
        metadata=FakeMetadata(
            {
                (
                    "host",
                    "server",
                ): root,
            }
        ),
    )

    result = service.impact(
        "host",
        "server",
    )

    assert result["root_metadata"] == root
    assert result["reviewed_impact_count"] == 0
    assert result["highest_criticality"] == "important"
    assert result["has_reviewed_continuity"] is True


def test_reviewed_affected_entities_are_included():
    application = metadata(
        "Application",
        "important",
    )

    graph = impact_graph(
        [
            {
                "entity_type": "application",
                "entity_id": "app",
                "depth": 1,
                "via_relationship": "runs_on",
                "path": [
                    {
                        "source_type": "application",
                        "source_id": "app",
                        "relationship_type": "runs_on",
                        "target_type": "host",
                        "target_id": "server",
                    }
                ],
            }
        ]
    )

    service = ContinuityImpactService(
        dependencies=FakeDependencies(
            graph
        ),
        metadata=FakeMetadata(
            {
                (
                    "application",
                    "app",
                ): application,
            }
        ),
    )

    result = service.impact(
        "host",
        "server",
    )

    assert result["graph_impact_count"] == 1
    assert result["reviewed_impact_count"] == 1

    assert (
        result["affected"][0]["entity_id"]
        == "app"
    )

    assert (
        result["affected"][0]["metadata"]
        == application
    )


def test_unreviewed_entities_are_not_given_invented_meaning():
    graph = impact_graph(
        [
            {
                "entity_type": "service",
                "entity_id": "unknown-service",
                "depth": 1,
                "via_relationship": "depends_on",
                "path": [],
            }
        ]
    )

    service = ContinuityImpactService(
        dependencies=FakeDependencies(
            graph
        ),
        metadata=FakeMetadata(
            {}
        ),
    )

    result = service.impact(
        "host",
        "server",
    )

    assert result["graph_impact_count"] == 1
    assert result["reviewed_impact_count"] == 0
    assert result["affected"] == []
    assert result["highest_criticality"] is None
    assert result["has_reviewed_continuity"] is False


def test_highest_criticality_uses_reviewed_metadata():
    root = metadata(
        "Server",
        "important",
    )

    critical_service = metadata(
        "Phone",
        "critical",
    )

    optional_service = metadata(
        "Media",
        "optional",
    )

    graph = impact_graph(
        [
            {
                "entity_type": "service",
                "entity_id": "phone",
                "depth": 1,
                "via_relationship": "runs_on",
                "path": [],
            },
            {
                "entity_type": "service",
                "entity_id": "media",
                "depth": 1,
                "via_relationship": "runs_on",
                "path": [],
            },
        ]
    )

    service = ContinuityImpactService(
        dependencies=FakeDependencies(
            graph
        ),
        metadata=FakeMetadata(
            {
                (
                    "host",
                    "server",
                ): root,
                (
                    "service",
                    "phone",
                ): critical_service,
                (
                    "service",
                    "media",
                ): optional_service,
            }
        ),
    )

    result = service.impact(
        "host",
        "server",
    )

    assert result["highest_criticality"] == "critical"


def test_max_depth_is_forwarded_to_dependency_service():
    service = ContinuityImpactService(
        dependencies=FakeDependencies(
            impact_graph()
        ),
        metadata=FakeMetadata(
            {}
        ),
    )

    result = service.impact(
        "host",
        "server",
        max_depth=2,
    )

    assert result["has_reviewed_continuity"] is False
    assert service.dependencies.last_max_depth == 2


def test_root_only_reviewed_metadata_does_not_invent_dependents():
    root = metadata(
        "Server",
        "important",
    )

    service = ContinuityImpactService(
        dependencies=FakeDependencies(
            impact_graph()
        ),
        metadata=FakeMetadata(
            {
                (
                    "host",
                    "server",
                ): root,
            }
        ),
    )

    result = service.impact(
        "host",
        "server",
    )

    assert result["affected"] == []
    assert result["graph_impact_count"] == 0
    assert result["reviewed_impact_count"] == 0


def test_unreviewed_entities_are_reported_as_unclassified():
    graph = impact_graph(
        [
            {
                "entity_type": "service",
                "entity_id": "unknown-service",
                "depth": 1,
                "via_relationship": "depends_on",
                "path": [],
            }
        ]
    )

    service = ContinuityImpactService(
        dependencies=FakeDependencies(
            graph
        ),
        metadata=FakeMetadata(
            {}
        ),
    )

    result = service.impact(
        "host",
        "server",
    )

    assert result["reviewed_impact_count"] == 0
    assert result["unclassified_impact_count"] == 1
    assert result["affected"] == []

    assert result["unclassified"] == [
        {
            "entity_type": "service",
            "entity_id": "unknown-service",
            "depth": 1,
            "via_relationship": "depends_on",
            "path": [],
        }
    ]


def test_all_reviewed_impacts_leave_no_unclassified_assets():
    application = metadata(
        "Application",
        "important",
    )

    graph = impact_graph(
        [
            {
                "entity_type": "application",
                "entity_id": "app",
                "depth": 1,
                "via_relationship": "runs_on",
                "path": [],
            }
        ]
    )

    service = ContinuityImpactService(
        dependencies=FakeDependencies(
            graph
        ),
        metadata=FakeMetadata(
            {
                (
                    "application",
                    "app",
                ): application,
            }
        ),
    )

    result = service.impact(
        "host",
        "server",
    )

    assert result["reviewed_impact_count"] == 1
    assert result["unclassified_impact_count"] == 0
    assert result["unclassified"] == []


def test_criticality_rank_uses_metadata_authority():
    assert (
        ContinuityImpactService._criticality_rank(
            "optional"
        )
        == 1
    )

    assert (
        ContinuityImpactService._criticality_rank(
            "important"
        )
        == 2
    )

    assert (
        ContinuityImpactService._criticality_rank(
            "critical"
        )
        == 3
    )

    assert (
        ContinuityImpactService._criticality_rank(
            "unknown"
        )
        == 0
    )
