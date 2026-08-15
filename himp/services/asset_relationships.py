"""
Asset Relationship Service.

Business logic layer for infrastructure asset relationships.
"""

from himp.database.asset_relationships import (
    AssetRelationshipRepository,
)
from himp.models.asset_relationship import (
    AssetRelationship,
)


class AssetRelationshipService:
    """
    Provides infrastructure asset relationship operations.
    """

    def __init__(
        self,
        repository=None,
    ):
        self.repository = (
            repository
            or AssetRelationshipRepository()
        )

    def add(
        self,
        source_type,
        source_id,
        relationship_type,
        target_type,
        target_id,
    ):
        values = {
            "source_type": source_type,
            "source_id": source_id,
            "relationship_type": relationship_type,
            "target_type": target_type,
            "target_id": target_id,
        }

        for name, value in values.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{name} must not be empty"
                )

        relationship = self.repository.add(
            source_type=source_type.strip(),
            source_id=source_id.strip(),
            relationship_type=relationship_type.strip(),
            target_type=target_type.strip(),
            target_id=target_id.strip(),
        )

        return AssetRelationship(
            source_type=relationship["source_type"],
            source_id=relationship["source_id"],
            relationship_type=relationship["relationship_type"],
            target_type=relationship["target_type"],
            target_id=relationship["target_id"],
        )

    def list(self):
        return [
            AssetRelationship(
                source_type=item["source_type"],
                source_id=item["source_id"],
                relationship_type=item["relationship_type"],
                target_type=item["target_type"],
                target_id=item["target_id"],
            )
            for item in self.repository.list()
        ]

    def list_for_source(
        self,
        source_type,
        source_id,
    ):
        return [
            AssetRelationship(
                source_type=item["source_type"],
                source_id=item["source_id"],
                relationship_type=item["relationship_type"],
                target_type=item["target_type"],
                target_id=item["target_id"],
            )
            for item in self.repository.list_for_source(
                source_type=source_type,
                source_id=source_id,
            )
        ]

    def list_for_target(
        self,
        target_type,
        target_id,
    ):
        return [
            AssetRelationship(
                source_type=item["source_type"],
                source_id=item["source_id"],
                relationship_type=item["relationship_type"],
                target_type=item["target_type"],
                target_id=item["target_id"],
            )
            for item in self.repository.list_for_target(
                target_type=target_type,
                target_id=target_id,
            )
        ]
