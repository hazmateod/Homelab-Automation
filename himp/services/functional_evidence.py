"""
Deterministic functional service evidence normalization.

Functional evidence describes whether a specific provider has
demonstrated that it can perform a service-related function.

This service does not collect evidence, infer provider membership,
evaluate service redundancy, modify topology, perform failover,
or perform remediation.
"""

from datetime import UTC, datetime, timedelta


class FunctionalEvidenceService:

    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"

    STATES = frozenset(
        {
            AVAILABLE,
            UNAVAILABLE,
            UNKNOWN,
        }
    )

    REQUIRED_FIELDS = frozenset(
        {
            "entity_type",
            "entity_id",
            "state",
            "evidence_type",
            "source",
            "observed_at",
            "fresh_for_seconds",
            "message",
            "details",
        }
    )

    @classmethod
    def _text(
        cls,
        value,
        field,
        lower=False,
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

        if lower:
            value = value.lower()

        return value

    @classmethod
    def _state(
        cls,
        value,
    ):
        value = cls._text(
            value,
            "state",
        ).upper()

        if value not in cls.STATES:
            raise ValueError(
                "Unsupported functional evidence state: "
                f"{value}"
            )

        return value

    @classmethod
    def _observed_at(
        cls,
        value,
    ):
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(
                    value.replace(
                        "Z",
                        "+00:00",
                    )
                )
            except ValueError as exc:
                raise ValueError(
                    "observed_at must be a valid "
                    "ISO 8601 datetime"
                ) from exc

        if not isinstance(value, datetime):
            raise ValueError(
                "observed_at must be a datetime "
                "or ISO 8601 string"
            )

        if value.tzinfo is None:
            raise ValueError(
                "observed_at must be timezone-aware"
            )

        return value.astimezone(UTC)

    @classmethod
    def _fresh_for_seconds(
        cls,
        value,
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 1
        ):
            raise ValueError(
                "fresh_for_seconds must be "
                "a positive integer"
            )

        return value

    @classmethod
    def normalize(
        cls,
        evidence,
        now=None,
    ):
        if not isinstance(evidence, dict):
            raise ValueError(
                "functional evidence must be a mapping"
            )

        missing = (
            cls.REQUIRED_FIELDS
            - evidence.keys()
        )

        if missing:
            raise ValueError(
                "functional evidence missing fields: "
                + ", ".join(sorted(missing))
            )

        unexpected = (
            evidence.keys()
            - cls.REQUIRED_FIELDS
        )

        if unexpected:
            raise ValueError(
                "functional evidence has unsupported fields: "
                + ", ".join(sorted(unexpected))
            )

        entity_type = cls._text(
            evidence["entity_type"],
            "entity_type",
            lower=True,
        )

        entity_id = cls._text(
            evidence["entity_id"],
            "entity_id",
        )

        state = cls._state(
            evidence["state"]
        )

        evidence_type = cls._text(
            evidence["evidence_type"],
            "evidence_type",
            lower=True,
        )

        source = cls._text(
            evidence["source"],
            "source",
            lower=True,
        )

        observed_at = cls._observed_at(
            evidence["observed_at"]
        )

        fresh_for_seconds = (
            cls._fresh_for_seconds(
                evidence[
                    "fresh_for_seconds"
                ]
            )
        )

        message = cls._text(
            evidence["message"],
            "message",
        )

        details = evidence["details"]

        if not isinstance(details, dict):
            raise ValueError(
                "details must be a mapping"
            )

        if now is None:
            now = datetime.now(UTC)
        else:
            now = cls._observed_at(now)

        expires_at = (
            observed_at
            + timedelta(
                seconds=fresh_for_seconds
            )
        )

        stale = now > expires_at

        effective_state = (
            cls.UNKNOWN
            if stale
            else state
        )

        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "state": effective_state,
            "reported_state": state,
            "evidence_type": evidence_type,
            "source": source,
            "observed_at": observed_at,
            "fresh_for_seconds": (
                fresh_for_seconds
            ),
            "expires_at": expires_at,
            "stale": stale,
            "message": message,
            "details": dict(details),
        }

    @classmethod
    def availability_evidence(
        cls,
        evidence,
        now=None,
    ):
        normalized = cls.normalize(
            evidence,
            now=now,
        )

        return {
            "entity_type": (
                normalized["entity_type"]
            ),
            "entity_id": (
                normalized["entity_id"]
            ),
            "state": normalized["state"],
        }
