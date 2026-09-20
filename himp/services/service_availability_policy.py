"""
Service availability policy.

Defines reviewed, deployment-managed policies describing how
multiple providers combine to make a service available.

This service defines policy only. It does not inspect health,
infer provider membership, modify topology, or perform recovery.
"""

from pathlib import Path

import yaml

from himp.services.asset_relationships import (
    AssetRelationshipService,
)


class ServiceAvailabilityPolicyService:

    ENTITY_TYPES = AssetRelationshipService.ENTITY_TYPES

    REQUIRED_FIELDS = frozenset(
        {
            "service_type",
            "service_id",
            "display_name",
            "minimum_available",
            "providers",
        }
    )

    PROVIDER_REQUIRED_FIELDS = frozenset(
        {
            "entity_type",
            "entity_id",
        }
    )

    def __init__(
        self,
        config_path=None,
    ):
        self.config_path = Path(
            config_path
            or "config/service_availability.yml"
        )

    @staticmethod
    def _text(
        value,
        field,
    ):
        if not isinstance(value, str):
            raise ValueError(
                f"{field} must be a non-empty string"
            )

        value = value.strip()

        if not value:
            raise ValueError(
                f"{field} must be a non-empty string"
            )

        return value

    @classmethod
    def _entity_type(
        cls,
        value,
        field,
    ):
        value = cls._text(
            value,
            field,
        ).lower()

        if value not in cls.ENTITY_TYPES:
            raise ValueError(
                f"Unsupported {field}: {value}"
            )

        return value

    @staticmethod
    def _minimum_available(
        value,
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 1
        ):
            raise ValueError(
                "minimum_available must be a "
                "positive integer"
            )

        return value

    @classmethod
    def _provider(
        cls,
        provider,
    ):
        if not isinstance(provider, dict):
            raise ValueError(
                "provider must be a mapping"
            )

        missing = (
            cls.PROVIDER_REQUIRED_FIELDS
            - provider.keys()
        )

        if missing:
            raise ValueError(
                "provider missing fields: "
                + ", ".join(sorted(missing))
            )

        unexpected = (
            provider.keys()
            - cls.PROVIDER_REQUIRED_FIELDS
        )

        if unexpected:
            raise ValueError(
                "provider has unsupported fields: "
                + ", ".join(sorted(unexpected))
            )

        return {
            "entity_type": cls._entity_type(
                provider["entity_type"],
                "provider entity_type",
            ),
            "entity_id": cls._text(
                provider["entity_id"],
                "provider entity_id",
            ),
        }

    @classmethod
    def _policy(
        cls,
        policy,
    ):
        if not isinstance(policy, dict):
            raise ValueError(
                "service availability policy "
                "must be a mapping"
            )

        missing = (
            cls.REQUIRED_FIELDS
            - policy.keys()
        )

        if missing:
            raise ValueError(
                "service availability policy "
                "missing fields: "
                + ", ".join(sorted(missing))
            )

        unexpected = (
            policy.keys()
            - cls.REQUIRED_FIELDS
        )

        if unexpected:
            raise ValueError(
                "service availability policy "
                "has unsupported fields: "
                + ", ".join(sorted(unexpected))
            )

        service_type = cls._entity_type(
            policy["service_type"],
            "service_type",
        )

        service_id = cls._text(
            policy["service_id"],
            "service_id",
        )

        display_name = cls._text(
            policy["display_name"],
            "display_name",
        )

        minimum_available = (
            cls._minimum_available(
                policy["minimum_available"]
            )
        )

        providers = policy["providers"]

        if not isinstance(providers, list):
            raise ValueError(
                "providers must be a list"
            )

        if not providers:
            raise ValueError(
                "providers must not be empty"
            )

        normalized_providers = []
        seen = set()

        for provider in providers:
            normalized = cls._provider(
                provider
            )

            key = (
                normalized["entity_type"],
                normalized["entity_id"],
            )

            if key in seen:
                raise ValueError(
                    "Duplicate service availability "
                    "provider: "
                    f"{key[0]}:{key[1]}"
                )

            seen.add(key)
            normalized_providers.append(
                normalized
            )

        if minimum_available > len(
            normalized_providers
        ):
            raise ValueError(
                "minimum_available cannot exceed "
                "provider count"
            )

        return {
            "service_type": service_type,
            "service_id": service_id,
            "display_name": display_name,
            "minimum_available": (
                minimum_available
            ),
            "providers": normalized_providers,
        }

    def load(
        self,
    ):
        raw = yaml.safe_load(
            self.config_path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(raw, dict):
            raise ValueError(
                "service availability configuration "
                "must be a mapping"
            )

        policies = raw.get(
            "services"
        )

        if not isinstance(policies, list):
            raise ValueError(
                "services must be a list"
            )

        result = {}

        for policy in policies:
            normalized = self._policy(
                policy
            )

            key = (
                normalized["service_type"],
                normalized["service_id"],
            )

            if key in result:
                raise ValueError(
                    "Duplicate service availability "
                    "policy: "
                    f"{key[0]}:{key[1]}"
                )

            result[key] = normalized

        return result

    def get(
        self,
        service_type,
        service_id,
    ):
        service_type = self._entity_type(
            service_type,
            "service_type",
        )

        service_id = self._text(
            service_id,
            "service_id",
        )

        return self.load().get(
            (
                service_type,
                service_id,
            )
        )
