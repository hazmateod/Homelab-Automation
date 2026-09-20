"""
Continuity Metadata Service.

Loads and validates deployment-specific continuity metadata.

Continuity metadata describes the human operational importance of
entities already known to HIMP. It does not define infrastructure
topology, contain credentials, execute remediation, or infer
relationships.

The Git-managed continuity metadata configuration is authoritative.
"""

from pathlib import Path

import yaml

from himp.services.asset_relationships import (
    AssetRelationshipService,
)


class ContinuityMetadataService:
    """
    Provides deterministic, reviewed continuity metadata.
    """

    ENTITY_TYPES = (
        AssetRelationshipService.ENTITY_TYPES
    )

    CRITICALITY_ORDER = {
        "optional": 1,
        "important": 2,
        "critical": 3,
    }

    CRITICALITY_LEVELS = frozenset(
        CRITICALITY_ORDER
    )

    RECOVERY_AUTHORITIES = frozenset(
        {
            "continuity_operator",
            "technical_only",
        }
    )

    REQUIRED_FIELDS = (
        "entity_type",
        "entity_id",
        "display_name",
        "continuity_role",
        "criticality",
        "household_impact",
        "recovery_authority",
        "can_wait",
    )

    def __init__(
        self,
        config_path=None,
    ):
        self.config_path = Path(
            config_path
            or "config/continuity_metadata.yml"
        )

    @staticmethod
    def _required_text(
        index,
        field,
        value,
    ):
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                "Continuity metadata entry "
                f"{index} field {field} "
                "must not be empty"
            )

        return value.strip()

    def _normalize_entry(
        self,
        index,
        item,
    ):
        if not isinstance(item, dict):
            raise ValueError(
                "Continuity metadata entry "
                f"{index} must be a mapping"
            )

        missing = [
            field
            for field in self.REQUIRED_FIELDS
            if field not in item
        ]

        if missing:
            raise ValueError(
                "Continuity metadata entry "
                f"{index} missing fields: "
                + ", ".join(missing)
            )

        normalized = {
            field: self._required_text(
                index,
                field,
                item[field],
            )
            for field in self.REQUIRED_FIELDS
        }

        normalized["entity_type"] = (
            normalized["entity_type"].lower()
        )

        normalized["criticality"] = (
            normalized["criticality"].lower()
        )

        normalized["recovery_authority"] = (
            normalized[
                "recovery_authority"
            ].lower()
        )

        if (
            normalized["entity_type"]
            not in self.ENTITY_TYPES
        ):
            raise ValueError(
                "Continuity metadata entry "
                f"{index} has unsupported "
                "entity_type: "
                f"{normalized['entity_type']}"
            )

        if (
            normalized["criticality"]
            not in self.CRITICALITY_LEVELS
        ):
            raise ValueError(
                "Continuity metadata entry "
                f"{index} has unsupported "
                "criticality: "
                f"{normalized['criticality']}"
            )

        if (
            normalized["recovery_authority"]
            not in self.RECOVERY_AUTHORITIES
        ):
            raise ValueError(
                "Continuity metadata entry "
                f"{index} has unsupported "
                "recovery_authority: "
                f"{normalized['recovery_authority']}"
            )

        return normalized

    @staticmethod
    def _key(item):
        return (
            item["entity_type"],
            item["entity_id"],
        )

    def load(self):
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
                "Continuity metadata configuration "
                "must be a mapping"
            )

        entities = data.get(
            "entities",
            [],
        )

        if not isinstance(entities, list):
            raise ValueError(
                "entities must be a list"
            )

        result = {}
        seen = set()

        for index, item in enumerate(
            entities,
            start=1,
        ):
            normalized = self._normalize_entry(
                index,
                item,
            )

            key = self._key(
                normalized
            )

            if key in seen:
                raise ValueError(
                    "Duplicate continuity metadata "
                    "entity: "
                    f"{key}"
                )

            seen.add(key)
            result[key] = normalized

        return result

    def get(
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

        key = (
            entity_type.strip().lower(),
            entity_id.strip(),
        )

        return self.load().get(
            key
        )
