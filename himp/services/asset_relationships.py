"""
Asset Relationship Service.

Business logic layer for canonical infrastructure relationships.
"""

from pathlib import Path

import yaml

from himp.config import config
from himp.database.asset_relationships import (
    AssetRelationshipRepository,
)
from himp.models.asset_relationship import (
    AssetRelationship,
)


class AssetRelationshipService:
    """
    Provides canonical infrastructure relationship operations.

    The Git-managed relationship configuration is authoritative.
    The asset_relationships database table is its synchronized
    operational representation.
    """

    ENTITY_TYPES = frozenset(
        {
            "application",
            "host",
            "service",
            "database",
            "dns",
            "storage",
            "backup",
        }
    )

    RELATIONSHIP_TYPES = frozenset(
        {
            "runs_on",
            "depends_on",
            "uses",
            "stores_on",
            "backed_up_by",
            "resolves_through",
            "provides",
        }
    )

    FIELDS = (
        "source_type",
        "source_id",
        "relationship_type",
        "target_type",
        "target_id",
    )

    def __init__(
        self,
        repository=None,
        config_path=None,
    ):
        self.repository = (
            repository
            or AssetRelationshipRepository()
        )

        self.config_path = Path(
            config_path
            or config.infrastructure_relationships
        )

    @staticmethod
    def _model(item):
        return AssetRelationship(
            source_type=item["source_type"],
            source_id=item["source_id"],
            relationship_type=item["relationship_type"],
            target_type=item["target_type"],
            target_id=item["target_id"],
        )

    @staticmethod
    def _key(relationship):
        return (
            relationship.source_type,
            relationship.source_id,
            relationship.relationship_type,
            relationship.target_type,
            relationship.target_id,
        )

    def _normalize(
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

        normalized = {
            "source_type": source_type.strip().lower(),
            "source_id": source_id.strip(),
            "relationship_type": (
                relationship_type.strip().lower()
            ),
            "target_type": target_type.strip().lower(),
            "target_id": target_id.strip(),
        }

        if (
            normalized["source_type"]
            not in self.ENTITY_TYPES
        ):
            raise ValueError(
                "Unsupported source_type: "
                f"{normalized['source_type']}"
            )

        if (
            normalized["target_type"]
            not in self.ENTITY_TYPES
        ):
            raise ValueError(
                "Unsupported target_type: "
                f"{normalized['target_type']}"
            )

        if (
            normalized["relationship_type"]
            not in self.RELATIONSHIP_TYPES
        ):
            raise ValueError(
                "Unsupported relationship_type: "
                f"{normalized['relationship_type']}"
            )

        if (
            normalized["source_type"]
            == normalized["target_type"]
            and normalized["source_id"]
            == normalized["target_id"]
        ):
            raise ValueError(
                "Asset relationship cannot target itself"
            )

        return normalized

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

        entity_type = entity_type.strip().lower()
        entity_id = entity_id.strip()

        if entity_type not in self.ENTITY_TYPES:
            raise ValueError(
                f"Unsupported entity_type: {entity_type}"
            )

        return entity_type, entity_id

    def add(
        self,
        source_type,
        source_id,
        relationship_type,
        target_type,
        target_id,
    ):
        values = self._normalize(
            source_type=source_type,
            source_id=source_id,
            relationship_type=relationship_type,
            target_type=target_type,
            target_id=target_id,
        )

        relationship = self.repository.add(
            **values
        )

        return self._model(relationship)

    def remove(
        self,
        source_type,
        source_id,
        relationship_type,
        target_type,
        target_id,
    ):
        values = self._normalize(
            source_type=source_type,
            source_id=source_id,
            relationship_type=relationship_type,
            target_type=target_type,
            target_id=target_id,
        )

        self.repository.remove(
            **values
        )

    def list(self):
        return [
            self._model(item)
            for item in self.repository.list()
        ]

    def list_for_source(
        self,
        source_type,
        source_id,
    ):
        source_type, source_id = (
            self._validate_entity(
                source_type,
                source_id,
            )
        )

        return [
            self._model(item)
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
        target_type, target_id = (
            self._validate_entity(
                target_type,
                target_id,
            )
        )

        return [
            self._model(item)
            for item in self.repository.list_for_target(
                target_type=target_type,
                target_id=target_id,
            )
        ]

    def load_desired(self):
        if not self.config_path.exists():
            raise FileNotFoundError(
                self.config_path
            )

        with self.config_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = yaml.safe_load(file) or {}

        if not isinstance(data, dict):
            raise ValueError(
                "Infrastructure relationship configuration "
                "must be a mapping"
            )

        relationships = data.get(
            "relationships",
            [],
        )

        if not isinstance(relationships, list):
            raise ValueError(
                "relationships must be a list"
            )

        desired = []
        seen = set()

        for index, item in enumerate(
            relationships,
            start=1,
        ):
            if not isinstance(item, dict):
                raise ValueError(
                    "Relationship entry "
                    f"{index} must be a mapping"
                )

            missing = [
                field
                for field in self.FIELDS
                if field not in item
            ]

            if missing:
                raise ValueError(
                    "Relationship entry "
                    f"{index} missing fields: "
                    + ", ".join(missing)
                )

            values = self._normalize(
                source_type=item["source_type"],
                source_id=item["source_id"],
                relationship_type=(
                    item["relationship_type"]
                ),
                target_type=item["target_type"],
                target_id=item["target_id"],
            )

            relationship = AssetRelationship(
                **values
            )

            key = self._key(
                relationship
            )

            if key in seen:
                raise ValueError(
                    "Duplicate infrastructure relationship "
                    f"in configuration: {key}"
                )

            seen.add(key)
            desired.append(relationship)

        return desired

    def reconcile(self):
        desired = self.load_desired()
        existing = self.list()

        desired_by_key = {
            self._key(item): item
            for item in desired
        }

        existing_by_key = {
            self._key(item): item
            for item in existing
        }

        desired_keys = set(
            desired_by_key
        )
        existing_keys = set(
            existing_by_key
        )

        remove_keys = sorted(
            existing_keys - desired_keys
        )

        add_keys = sorted(
            desired_keys - existing_keys
        )

        for key in remove_keys:
            relationship = existing_by_key[
                key
            ]

            self.repository.remove(
                source_type=relationship.source_type,
                source_id=relationship.source_id,
                relationship_type=(
                    relationship.relationship_type
                ),
                target_type=relationship.target_type,
                target_id=relationship.target_id,
            )

        for key in add_keys:
            relationship = desired_by_key[
                key
            ]

            self.repository.add(
                source_type=relationship.source_type,
                source_id=relationship.source_id,
                relationship_type=(
                    relationship.relationship_type
                ),
                target_type=relationship.target_type,
                target_id=relationship.target_id,
            )

        final = self.list()

        return {
            "configured": len(desired),
            "added": len(add_keys),
            "removed": len(remove_keys),
            "unchanged": len(
                desired_keys & existing_keys
            ),
            "total": len(final),
            "relationships": final,
        }
