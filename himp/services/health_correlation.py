"""
Health Correlation Service.

Correlates asset relationships with the health state of related
host assets.
"""

from himp.services.asset_relationships import (
    AssetRelationshipService,
)
from himp.services.host_health import HostHealthService


class HealthCorrelationService:
    """
    Correlates related infrastructure assets with health state.
    """

    def __init__(
        self,
        relationships=None,
        health=None,
    ):
        self.relationships = (
            relationships
            or AssetRelationshipService()
        )

        self.health = (
            health
            or HostHealthService()
        )

    def correlate(
        self,
        source_type,
        source_id,
    ):
        relationships = (
            self.relationships.list_for_source(
                source_type=source_type,
                source_id=source_id,
            )
        )

        correlated = []

        for relationship in relationships:

            health_status = "UNKNOWN"

            if (
                relationship.target_type == "host"
            ):
                result = self.health.latest(
                    relationship.target_id
                )

                if result is not None:
                    health_status = result["status"]

            correlated.append(
                {
                    "source_type": (
                        relationship.source_type
                    ),
                    "source_id": (
                        relationship.source_id
                    ),
                    "relationship_type": (
                        relationship.relationship_type
                    ),
                    "target_type": (
                        relationship.target_type
                    ),
                    "target_id": (
                        relationship.target_id
                    ),
                    "health_status": health_status,
                }
            )

        return {
            "source_type": source_type,
            "source_id": source_id,
            "relationships": correlated,
        }
