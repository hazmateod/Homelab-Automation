"""
Deterministic service availability evaluation.

Consumes an explicit reviewed service availability policy and
explicit provider evidence.

This service does not collect health, infer provider membership,
modify topology, perform failover, or perform remediation.
"""


class ServiceAvailabilityService:

    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"

    STATES = frozenset(
        {
            AVAILABLE,
            DEGRADED,
            UNAVAILABLE,
            UNKNOWN,
        }
    )

    @classmethod
    def _provider_key(
        cls,
        entity_type,
        entity_id,
    ):
        if not isinstance(entity_type, str):
            raise ValueError(
                "entity_type must be a non-empty string"
            )

        if not isinstance(entity_id, str):
            raise ValueError(
                "entity_id must be a non-empty string"
            )

        entity_type = entity_type.strip().lower()
        entity_id = entity_id.strip()

        if not entity_type:
            raise ValueError(
                "entity_type must be a non-empty string"
            )

        if not entity_id:
            raise ValueError(
                "entity_id must be a non-empty string"
            )

        return (
            entity_type,
            entity_id,
        )

    @classmethod
    def _evidence_state(
        cls,
        value,
    ):
        if not isinstance(value, str):
            raise ValueError(
                "provider evidence state must be a string"
            )

        value = value.strip().upper()

        if value not in cls.STATES:
            raise ValueError(
                "Unsupported provider evidence state: "
                f"{value}"
            )

        if value == cls.DEGRADED:
            raise ValueError(
                "Provider evidence cannot use DEGRADED; "
                "DEGRADED is a service aggregate state"
            )

        return value

    @classmethod
    def _normalize_evidence(
        cls,
        evidence,
    ):
        if not isinstance(evidence, list):
            raise ValueError(
                "evidence must be a list"
            )

        result = {}

        for item in evidence:
            if not isinstance(item, dict):
                raise ValueError(
                    "provider evidence must be a mapping"
                )

            required = {
                "entity_type",
                "entity_id",
                "state",
            }

            missing = required - item.keys()

            if missing:
                raise ValueError(
                    "provider evidence missing fields: "
                    + ", ".join(sorted(missing))
                )

            unexpected = item.keys() - required

            if unexpected:
                raise ValueError(
                    "provider evidence has unsupported fields: "
                    + ", ".join(sorted(unexpected))
                )

            key = cls._provider_key(
                item["entity_type"],
                item["entity_id"],
            )

            if key in result:
                raise ValueError(
                    "Duplicate provider evidence: "
                    f"{key[0]}:{key[1]}"
                )

            result[key] = cls._evidence_state(
                item["state"]
            )

        return result

    @classmethod
    def evaluate(
        cls,
        policy,
        evidence,
    ):
        if not isinstance(policy, dict):
            raise ValueError(
                "policy must be a mapping"
            )

        required = {
            "service_type",
            "service_id",
            "display_name",
            "minimum_available",
            "providers",
        }

        missing = required - policy.keys()

        if missing:
            raise ValueError(
                "policy missing fields: "
                + ", ".join(sorted(missing))
            )

        providers = policy["providers"]

        if not isinstance(providers, list):
            raise ValueError(
                "policy providers must be a list"
            )

        if not providers:
            raise ValueError(
                "policy providers must not be empty"
            )

        minimum_available = policy[
            "minimum_available"
        ]

        if (
            isinstance(minimum_available, bool)
            or not isinstance(
                minimum_available,
                int,
            )
            or minimum_available < 1
        ):
            raise ValueError(
                "policy minimum_available must be "
                "a positive integer"
            )

        if minimum_available > len(providers):
            raise ValueError(
                "policy minimum_available cannot "
                "exceed provider count"
            )

        normalized_evidence = (
            cls._normalize_evidence(
                evidence
            )
        )

        provider_results = []
        available = 0
        unavailable = 0
        unknown = 0

        policy_keys = set()

        for provider in providers:
            if not isinstance(provider, dict):
                raise ValueError(
                    "policy provider must be a mapping"
                )

            if set(provider) != {
                "entity_type",
                "entity_id",
            }:
                raise ValueError(
                    "policy provider must contain only "
                    "entity_type and entity_id"
                )

            key = cls._provider_key(
                provider["entity_type"],
                provider["entity_id"],
            )

            if key in policy_keys:
                raise ValueError(
                    "Duplicate policy provider: "
                    f"{key[0]}:{key[1]}"
                )

            policy_keys.add(key)

            state = normalized_evidence.get(
                key,
                cls.UNKNOWN,
            )

            if state == cls.AVAILABLE:
                available += 1
            elif state == cls.UNAVAILABLE:
                unavailable += 1
            else:
                unknown += 1

            provider_results.append(
                {
                    "entity_type": key[0],
                    "entity_id": key[1],
                    "state": state,
                }
            )

        unexpected_evidence = (
            normalized_evidence.keys()
            - policy_keys
        )

        if unexpected_evidence:
            key = sorted(
                unexpected_evidence
            )[0]

            raise ValueError(
                "Evidence supplied for provider "
                "outside policy: "
                f"{key[0]}:{key[1]}"
            )

        if available >= minimum_available:
            if unavailable > 0:
                state = cls.DEGRADED
            else:
                state = cls.AVAILABLE
        elif (
            available + unknown
            >= minimum_available
        ):
            state = cls.UNKNOWN
        else:
            state = cls.UNAVAILABLE

        return {
            "service_type": policy["service_type"],
            "service_id": policy["service_id"],
            "display_name": policy["display_name"],
            "state": state,
            "minimum_available": minimum_available,
            "provider_count": len(providers),
            "available_count": available,
            "unavailable_count": unavailable,
            "unknown_count": unknown,
            "evidence_complete": unknown == 0,
            "providers": provider_results,
        }
