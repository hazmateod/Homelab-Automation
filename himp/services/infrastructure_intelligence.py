"""
Infrastructure Intelligence Service.

Aggregates asset relationships, related health,
inventory changes, and deterministic baseline drift.
"""

from himp.services.asset_relationships import (
    AssetRelationshipService,
)
from himp.services.health_correlation import (
    HealthCorrelationService,
)
from himp.services.inventory import InventoryService
from himp.services.inventory_baseline import (
    InventoryBaselineService,
)
from himp.database.inventory_baseline import (
    InventoryBaselineRepository,
)


class InfrastructureIntelligenceService:
    """
    Provides a deterministic infrastructure intelligence view
    by composing existing HIMP services.
    """

    def __init__(
        self,
        relationships=None,
        inventory=None,
        health=None,
        baseline=None,
    ):
        self.relationships = (
            relationships
            or AssetRelationshipService()
        )

        self.inventory = (
            inventory
            or InventoryService()
        )

        self.health = (
            health
            or HealthCorrelationService(
                relationships=self.relationships,
            )
        )

        self.baseline = (
            baseline
            or InventoryBaselineService(
                inventory=self.inventory.repository,
                repository=InventoryBaselineRepository(),
            )
        )

    def inspect(
        self,
        source_type,
        source_id,
        baseline=None,
        change_limit=10,
    ):
        health = self.health.correlate(
            source_type=source_type,
            source_id=source_id,
        )

        changes = self.inventory.changes(
            limit=change_limit,
        )

        drift = []

        if baseline is not None:
            comparison = self.baseline.compare(
                baseline,
            )

            drift = comparison["drift"]

        return {
            "source_type": source_type,
            "source_id": source_id,
            "relationships": health["relationships"],
            "changes": changes,
            "drift": drift,
        }
