import pytest

from himp.services.service_availability import (
    ServiceAvailabilityService,
)


def policy(
    minimum_available=1,
):
    return {
        "service_type": "service",
        "service_id": "example_service",
        "display_name": "Example Service",
        "minimum_available": minimum_available,
        "providers": [
            {
                "entity_type": "host",
                "entity_id": "provider-a",
            },
            {
                "entity_type": "host",
                "entity_id": "provider-b",
            },
        ],
    }


def evidence(
    a=None,
    b=None,
):
    result = []

    if a is not None:
        result.append(
            {
                "entity_type": "host",
                "entity_id": "provider-a",
                "state": a,
            }
        )

    if b is not None:
        result.append(
            {
                "entity_type": "host",
                "entity_id": "provider-b",
                "state": b,
            }
        )

    return result


def test_all_providers_available():
    result = (
        ServiceAvailabilityService.evaluate(
            policy(),
            evidence(
                "AVAILABLE",
                "AVAILABLE",
            ),
        )
    )

    assert result["state"] == "AVAILABLE"
    assert result["available_count"] == 2
    assert result["unavailable_count"] == 0
    assert result["unknown_count"] == 0
    assert result["evidence_complete"] is True


def test_redundancy_loss_is_degraded():
    result = (
        ServiceAvailabilityService.evaluate(
            policy(),
            evidence(
                "AVAILABLE",
                "UNAVAILABLE",
            ),
        )
    )

    assert result["state"] == "DEGRADED"
    assert result["available_count"] == 1
    assert result["unavailable_count"] == 1


def test_unknown_provider_with_satisfied_minimum_remains_available():
    result = (
        ServiceAvailabilityService.evaluate(
            policy(),
            evidence(
                "AVAILABLE",
                "UNKNOWN",
            ),
        )
    )

    assert result["state"] == "AVAILABLE"
    assert result["evidence_complete"] is False


def test_missing_evidence_is_unknown():
    result = (
        ServiceAvailabilityService.evaluate(
            policy(),
            evidence(),
        )
    )

    assert result["state"] == "UNKNOWN"
    assert result["unknown_count"] == 2


def test_unknown_can_still_satisfy_minimum():
    result = (
        ServiceAvailabilityService.evaluate(
            policy(
                minimum_available=2
            ),
            evidence(
                "AVAILABLE",
                None,
            ),
        )
    )

    assert result["state"] == "UNKNOWN"
    assert result["available_count"] == 1
    assert result["unknown_count"] == 1


def test_confirmed_failure_below_minimum_is_unavailable():
    result = (
        ServiceAvailabilityService.evaluate(
            policy(
                minimum_available=2
            ),
            evidence(
                "AVAILABLE",
                "UNAVAILABLE",
            ),
        )
    )

    assert result["state"] == "UNAVAILABLE"


def test_all_providers_unavailable():
    result = (
        ServiceAvailabilityService.evaluate(
            policy(),
            evidence(
                "UNAVAILABLE",
                "UNAVAILABLE",
            ),
        )
    )

    assert result["state"] == "UNAVAILABLE"


def test_provider_identity_is_normalized():
    supplied = [
        {
            "entity_type": " Host ",
            "entity_id": " provider-a ",
            "state": " available ",
        },
        {
            "entity_type": "host",
            "entity_id": "provider-b",
            "state": "AVAILABLE",
        },
    ]

    result = (
        ServiceAvailabilityService.evaluate(
            policy(),
            supplied,
        )
    )

    assert result["state"] == "AVAILABLE"


def test_missing_single_provider_evidence_is_unknown():
    result = (
        ServiceAvailabilityService.evaluate(
            policy(
                minimum_available=2
            ),
            evidence(
                "AVAILABLE",
                None,
            ),
        )
    )

    provider_b = result["providers"][1]

    assert provider_b["state"] == "UNKNOWN"


def test_rejects_evidence_outside_policy():
    supplied = evidence(
        "AVAILABLE",
        "AVAILABLE",
    )

    supplied.append(
        {
            "entity_type": "host",
            "entity_id": "provider-c",
            "state": "AVAILABLE",
        }
    )

    with pytest.raises(
        ValueError,
        match="outside policy",
    ):
        ServiceAvailabilityService.evaluate(
            policy(),
            supplied,
        )


def test_rejects_duplicate_evidence():
    supplied = evidence(
        "AVAILABLE",
        None,
    )

    supplied.append(
        {
            "entity_type": "host",
            "entity_id": "provider-a",
            "state": "AVAILABLE",
        }
    )

    with pytest.raises(
        ValueError,
        match="Duplicate provider evidence",
    ):
        ServiceAvailabilityService.evaluate(
            policy(),
            supplied,
        )


def test_rejects_degraded_as_provider_evidence():
    with pytest.raises(
        ValueError,
        match="aggregate state",
    ):
        ServiceAvailabilityService.evaluate(
            policy(),
            evidence(
                "DEGRADED",
                "AVAILABLE",
            ),
        )


def test_rejects_unknown_evidence_state():
    with pytest.raises(
        ValueError,
        match="Unsupported provider evidence state",
    ):
        ServiceAvailabilityService.evaluate(
            policy(),
            evidence(
                "BROKEN",
                "AVAILABLE",
            ),
        )


def test_rejects_non_list_evidence():
    with pytest.raises(
        ValueError,
        match="evidence must be a list",
    ):
        ServiceAvailabilityService.evaluate(
            policy(),
            {},
        )


def test_rejects_non_mapping_evidence():
    with pytest.raises(
        ValueError,
        match="provider evidence must be a mapping",
    ):
        ServiceAvailabilityService.evaluate(
            policy(),
            [
                "invalid",
            ],
        )


def test_rejects_missing_evidence_field():
    with pytest.raises(
        ValueError,
        match="missing fields",
    ):
        ServiceAvailabilityService.evaluate(
            policy(),
            [
                {
                    "entity_type": "host",
                    "entity_id": "provider-a",
                }
            ],
        )


def test_rejects_extra_evidence_field():
    with pytest.raises(
        ValueError,
        match="unsupported fields",
    ):
        ServiceAvailabilityService.evaluate(
            policy(),
            [
                {
                    "entity_type": "host",
                    "entity_id": "provider-a",
                    "state": "AVAILABLE",
                    "invented": True,
                }
            ],
        )


def test_rejects_invalid_policy_minimum():
    invalid = policy()
    invalid["minimum_available"] = 0

    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        ServiceAvailabilityService.evaluate(
            invalid,
            [],
        )


def test_rejects_policy_minimum_above_provider_count():
    invalid = policy()
    invalid["minimum_available"] = 3

    with pytest.raises(
        ValueError,
        match="cannot exceed provider count",
    ):
        ServiceAvailabilityService.evaluate(
            invalid,
            [],
        )


def test_rejects_duplicate_policy_provider():
    invalid = policy()

    invalid["providers"].append(
        {
            "entity_type": " Host ",
            "entity_id": "provider-a",
        }
    )

    with pytest.raises(
        ValueError,
        match="Duplicate policy provider",
    ):
        ServiceAvailabilityService.evaluate(
            invalid,
            [],
        )


def test_result_preserves_service_identity():
    result = (
        ServiceAvailabilityService.evaluate(
            policy(),
            evidence(
                "AVAILABLE",
                "AVAILABLE",
            ),
        )
    )

    assert result["service_type"] == "service"
    assert result["service_id"] == "example_service"
    assert result["display_name"] == "Example Service"
    assert result["provider_count"] == 2
