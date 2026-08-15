import pytest

from himp.models.asset_relationship import AssetRelationship
from himp.services.health_correlation import HealthCorrelationService


def relationship(
    source_type,
    source_id,
    relationship_type,
    target_type,
    target_id,
):
    return AssetRelationship(
        source_type=source_type,
        source_id=source_id,
        relationship_type=relationship_type,
        target_type=target_type,
        target_id=target_id,
    )


def test_health_correlation_identifies_failed_related_asset():
    class FakeRelationshipService:
        def list_for_source(
            self,
            source_type,
            source_id,
        ):
            return [
                relationship(
                    "host",
                    "pve01",
                    "depends_on",
                    "host",
                    "pve02",
                ),
            ]

    class FakeHealthService:
        def latest(self, hostname):
            assert hostname == "pve02"

            return {
                "hostname": hostname,
                "status": "FAIL",
            }

    service = HealthCorrelationService(
        relationships=FakeRelationshipService(),
        health=FakeHealthService(),
    )

    result = service.correlate(
        source_type="host",
        source_id="pve01",
    )

    assert result["source_type"] == "host"
    assert result["source_id"] == "pve01"
    assert len(result["relationships"]) == 1
    assert result["relationships"][0]["target_id"] == "pve02"
    assert result["relationships"][0]["health_status"] == "FAIL"


def test_health_correlation_reports_unknown_when_no_health_exists():
    class FakeRelationshipService:
        def list_for_source(
            self,
            source_type,
            source_id,
        ):
            return [
                relationship(
                    "host",
                    "pve01",
                    "depends_on",
                    "host",
                    "pve02",
                ),
            ]

    class FakeHealthService:
        def latest(self, hostname):
            return None

    service = HealthCorrelationService(
        relationships=FakeRelationshipService(),
        health=FakeHealthService(),
    )

    result = service.correlate(
        source_type="host",
        source_id="pve01",
    )

    assert result["relationships"][0]["target_id"] == "pve02"
    assert result["relationships"][0]["health_status"] == "UNKNOWN"


def test_health_correlation_returns_empty_relationships():
    class FakeRelationshipService:
        def list_for_source(
            self,
            source_type,
            source_id,
        ):
            return []

    class FakeHealthService:
        def latest(self, hostname):
            raise AssertionError(
                "health lookup should not run"
            )

    service = HealthCorrelationService(
        relationships=FakeRelationshipService(),
        health=FakeHealthService(),
    )

    result = service.correlate(
        source_type="host",
        source_id="pve01",
    )

    assert result == {
        "source_type": "host",
        "source_id": "pve01",
        "relationships": [],
    }
