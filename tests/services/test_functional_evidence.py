from datetime import UTC, datetime

import pytest

from himp.services.functional_evidence import (
    FunctionalEvidenceService,
)


NOW = datetime(
    2026,
    9,
    20,
    6,
    0,
    0,
    tzinfo=UTC,
)


def evidence(
    **overrides,
):
    result = {
        "entity_type": "host",
        "entity_id": "provider-a",
        "state": "AVAILABLE",
        "evidence_type": "example_probe",
        "source": "example_collector",
        "observed_at": (
            "2026-09-20T05:59:30Z"
        ),
        "fresh_for_seconds": 60,
        "message": (
            "Provider passed functional probe."
        ),
        "details": {
            "example": True,
        },
    }

    result.update(overrides)

    return result


def test_normalizes_fresh_available_evidence():
    result = (
        FunctionalEvidenceService.normalize(
            evidence(),
            now=NOW,
        )
    )

    assert result["state"] == "AVAILABLE"
    assert (
        result["reported_state"]
        == "AVAILABLE"
    )
    assert result["stale"] is False
    assert result["entity_type"] == "host"
    assert result["entity_id"] == "provider-a"
    assert (
        result["evidence_type"]
        == "example_probe"
    )
    assert (
        result["source"]
        == "example_collector"
    )


def test_normalizes_unavailable_evidence():
    result = (
        FunctionalEvidenceService.normalize(
            evidence(
                state="UNAVAILABLE"
            ),
            now=NOW,
        )
    )

    assert result["state"] == "UNAVAILABLE"
    assert result["stale"] is False


def test_normalizes_unknown_evidence():
    result = (
        FunctionalEvidenceService.normalize(
            evidence(
                state="UNKNOWN"
            ),
            now=NOW,
        )
    )

    assert result["state"] == "UNKNOWN"
    assert result["stale"] is False


def test_stale_available_evidence_fails_closed():
    result = (
        FunctionalEvidenceService.normalize(
            evidence(
                observed_at=(
                    "2026-09-20T05:58:00Z"
                ),
                fresh_for_seconds=60,
            ),
            now=NOW,
        )
    )

    assert (
        result["reported_state"]
        == "AVAILABLE"
    )
    assert result["state"] == "UNKNOWN"
    assert result["stale"] is True


def test_stale_unavailable_evidence_fails_closed():
    result = (
        FunctionalEvidenceService.normalize(
            evidence(
                state="UNAVAILABLE",
                observed_at=(
                    "2026-09-20T05:58:00Z"
                ),
                fresh_for_seconds=60,
            ),
            now=NOW,
        )
    )

    assert (
        result["reported_state"]
        == "UNAVAILABLE"
    )
    assert result["state"] == "UNKNOWN"
    assert result["stale"] is True


def test_evidence_is_fresh_at_expiration_boundary():
    result = (
        FunctionalEvidenceService.normalize(
            evidence(
                observed_at=(
                    "2026-09-20T05:59:00Z"
                ),
                fresh_for_seconds=60,
            ),
            now=NOW,
        )
    )

    assert result["state"] == "AVAILABLE"
    assert result["stale"] is False


def test_accepts_timezone_aware_datetime():
    result = (
        FunctionalEvidenceService.normalize(
            evidence(
                observed_at=datetime(
                    2026,
                    9,
                    20,
                    5,
                    59,
                    30,
                    tzinfo=UTC,
                )
            ),
            now=NOW,
        )
    )

    assert (
        result["observed_at"].tzinfo
        is UTC
    )


def test_normalizes_identity_and_contract_text():
    result = (
        FunctionalEvidenceService.normalize(
            evidence(
                entity_type=" Host ",
                entity_id=" provider-a ",
                state=" available ",
                evidence_type=(
                    " Example_Probe "
                ),
                source=(
                    " Example_Collector "
                ),
            ),
            now=NOW,
        )
    )

    assert result["entity_type"] == "host"
    assert result["entity_id"] == "provider-a"
    assert result["state"] == "AVAILABLE"
    assert (
        result["evidence_type"]
        == "example_probe"
    )
    assert (
        result["source"]
        == "example_collector"
    )


def test_availability_evidence_returns_minimal_contract():
    result = (
        FunctionalEvidenceService.availability_evidence(
            evidence(),
            now=NOW,
        )
    )

    assert result == {
        "entity_type": "host",
        "entity_id": "provider-a",
        "state": "AVAILABLE",
    }


def test_stale_availability_evidence_returns_unknown():
    result = (
        FunctionalEvidenceService.availability_evidence(
            evidence(
                observed_at=(
                    "2026-09-20T05:00:00Z"
                )
            ),
            now=NOW,
        )
    )

    assert result == {
        "entity_type": "host",
        "entity_id": "provider-a",
        "state": "UNKNOWN",
    }


def test_rejects_non_mapping_evidence():
    with pytest.raises(
        ValueError,
        match="must be a mapping",
    ):
        FunctionalEvidenceService.normalize(
            [],
            now=NOW,
        )


def test_rejects_missing_field():
    invalid = evidence()
    del invalid["source"]

    with pytest.raises(
        ValueError,
        match="missing fields",
    ):
        FunctionalEvidenceService.normalize(
            invalid,
            now=NOW,
        )


def test_rejects_extra_field():
    invalid = evidence()
    invalid["invented"] = True

    with pytest.raises(
        ValueError,
        match="unsupported fields",
    ):
        FunctionalEvidenceService.normalize(
            invalid,
            now=NOW,
        )


@pytest.mark.parametrize(
    "field",
    [
        "entity_type",
        "entity_id",
        "evidence_type",
        "source",
        "message",
    ],
)
def test_rejects_empty_required_text(
    field,
):
    invalid = evidence()
    invalid[field] = " "

    with pytest.raises(
        ValueError,
        match=field,
    ):
        FunctionalEvidenceService.normalize(
            invalid,
            now=NOW,
        )


@pytest.mark.parametrize(
    "state",
    [
        "DEGRADED",
        "BROKEN",
        "",
    ],
)
def test_rejects_unsupported_state(
    state,
):
    with pytest.raises(ValueError):
        FunctionalEvidenceService.normalize(
            evidence(
                state=state
            ),
            now=NOW,
        )


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        True,
        "60",
    ],
)
def test_rejects_invalid_freshness(
    value,
):
    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        FunctionalEvidenceService.normalize(
            evidence(
                fresh_for_seconds=value
            ),
            now=NOW,
        )


def test_rejects_invalid_observation_time():
    with pytest.raises(
        ValueError,
        match="ISO 8601",
    ):
        FunctionalEvidenceService.normalize(
            evidence(
                observed_at="not-a-time"
            ),
            now=NOW,
        )


def test_rejects_naive_observation_time():
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        FunctionalEvidenceService.normalize(
            evidence(
                observed_at=datetime(
                    2026,
                    9,
                    20,
                    5,
                    59,
                    30,
                )
            ),
            now=NOW,
        )


def test_rejects_non_mapping_details():
    with pytest.raises(
        ValueError,
        match="details must be a mapping",
    ):
        FunctionalEvidenceService.normalize(
            evidence(
                details=[]
            ),
            now=NOW,
        )


def test_fresh_evidence_satisfies_availability_contract():
    from himp.services.service_availability import (
        ServiceAvailabilityService,
    )

    functional = (
        FunctionalEvidenceService.availability_evidence(
            evidence(),
            now=NOW,
        )
    )

    policy = {
        "service_type": "service",
        "service_id": "example_service",
        "display_name": "Example Service",
        "minimum_available": 1,
        "providers": [
            {
                "entity_type": "host",
                "entity_id": "provider-a",
            }
        ],
    }

    result = ServiceAvailabilityService.evaluate(
        policy,
        [functional],
    )

    assert result["state"] == "AVAILABLE"
    assert result["available_count"] == 1
    assert result["unknown_count"] == 0


def test_stale_evidence_cannot_satisfy_availability_contract():
    from himp.services.service_availability import (
        ServiceAvailabilityService,
    )

    functional = (
        FunctionalEvidenceService.availability_evidence(
            evidence(
                observed_at=(
                    "2026-09-20T05:00:00Z"
                )
            ),
            now=NOW,
        )
    )

    policy = {
        "service_type": "service",
        "service_id": "example_service",
        "display_name": "Example Service",
        "minimum_available": 1,
        "providers": [
            {
                "entity_type": "host",
                "entity_id": "provider-a",
            }
        ],
    }

    result = ServiceAvailabilityService.evaluate(
        policy,
        [functional],
    )

    assert result["state"] == "UNKNOWN"
    assert result["available_count"] == 0
    assert result["unknown_count"] == 1


def test_host_connectivity_shape_is_not_functional_evidence():
    connectivity = {
        "entity_type": "host",
        "entity_id": "provider-a",
        "state": "AVAILABLE",
        "source": "HOST_CONNECTIVITY",
    }

    with pytest.raises(
        ValueError,
        match="missing fields",
    ):
        FunctionalEvidenceService.normalize(
            connectivity,
            now=NOW,
        )
