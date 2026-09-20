"""
Continuity Impact Service.

Combines HIMP's canonical dependency graph with reviewed continuity
metadata to describe deterministic household operational impact.

This service is read-only. It does not infer topology, execute
remediation, or manufacture continuity meaning for entities that do
not have reviewed metadata.
"""

from himp.services.continuity_metadata import (
    ContinuityMetadataService,
)
from himp.services.dependency_impact import (
    DependencyImpactService,
)


class ContinuityImpactService:
    """
    Translate infrastructure impact into reviewed continuity impact.
    """

    def __init__(
        self,
        dependencies=None,
        metadata=None,
    ):
        self.dependencies = (
            dependencies
            or DependencyImpactService()
        )

        self.metadata = (
            metadata
            or ContinuityMetadataService()
        )

    @classmethod
    def _criticality_rank(
        cls,
        criticality,
    ):
        return (
            ContinuityMetadataService
            .CRITICALITY_ORDER
            .get(
                criticality,
                0,
            )
        )

    def impact(
        self,
        entity_type,
        entity_id,
        max_depth=None,
    ):
        graph = self.dependencies.impact(
            entity_type,
            entity_id,
            max_depth=max_depth,
        )

        root_metadata = self.metadata.get(
            graph["entity_type"],
            graph["entity_id"],
        )

        affected = []
        unclassified = []

        for asset in graph["assets"]:
            metadata = self.metadata.get(
                asset["entity_type"],
                asset["entity_id"],
            )

            if metadata is None:
                unclassified.append(
                    {
                        "entity_type": asset["entity_type"],
                        "entity_id": asset["entity_id"],
                        "depth": asset["depth"],
                        "via_relationship": (
                            asset["via_relationship"]
                        ),
                        "path": asset["path"],
                    }
                )
                continue

            affected.append(
                {
                    "entity_type": asset["entity_type"],
                    "entity_id": asset["entity_id"],
                    "depth": asset["depth"],
                    "via_relationship": (
                        asset["via_relationship"]
                    ),
                    "path": asset["path"],
                    "metadata": metadata,
                }
            )

        reviewed = []

        if root_metadata is not None:
            reviewed.append(
                {
                    "entity_type": graph["entity_type"],
                    "entity_id": graph["entity_id"],
                    "depth": 0,
                    "metadata": root_metadata,
                }
            )

        reviewed.extend(
            affected
        )

        highest_criticality = None

        if reviewed:
            highest_criticality = max(
                (
                    item["metadata"]["criticality"]
                    for item in reviewed
                ),
                key=self._criticality_rank,
            )

        return {
            "entity_type": graph["entity_type"],
            "entity_id": graph["entity_id"],
            "direction": "impact",
            "graph_impact_count": graph["count"],
            "reviewed_impact_count": len(affected),
            "unclassified_impact_count": len(
                unclassified
            ),
            "root_metadata": root_metadata,
            "affected": affected,
            "unclassified": unclassified,
            "highest_criticality": highest_criticality,
            "has_reviewed_continuity": bool(reviewed),
        }
