from datetime import UTC, datetime

import pytest

from plugins.freepbx.python.functional_evidence import (
    FreePBXFunctionalEvidence,
)


NOW = datetime(
    2026,
    9,
    20,
    7,
    0,
    0,
    tzinfo=UTC,
)

OBSERVED_AT = datetime(
    2026,
    9,
    20,
    6,
    59,
    30,
    tzinfo=UTC,
)


def build_evidence(
    item,
    observed_at=OBSERVED_AT,
    now=NOW,
):
    return FreePBXFunctionalEvidence.build(
        item,
        observed_at=observed_at,
        entity_type="host",
        entity_id="freepbx",
        now=now,
    )


def observation(
    **overrides,
):
    result = {
        "service_id": "home_telephone",
        "evidence_type": "sip_registration",
        "fresh_for_seconds": 600,
        "asterisk_cli": {
            "successful": True,
            "output": "System uptime: 2 weeks",
        },
        "registration": {
            "id": "555820_home",
            "successful": True,
            "output": (
                " 555820_home/"
                "sip:provider.example:5060"
                " 555820_home"
                " Registered"
                " (exp. 300s)"
            ),
        },
    }

    result.update(overrides)

    return result


def test_registered_trunk_is_available():
    result = build_evidence(
            observation(),
            observed_at=OBSERVED_AT,
            now=NOW,
        )

    assert result["state"] == "AVAILABLE"
    assert result["reported_state"] == "AVAILABLE"
    assert result["entity_type"] == "host"
    assert result["entity_id"] == "freepbx"
    assert result["source"] == "freepbx"
    assert (
        result["evidence_type"]
        == "sip_registration"
    )
    assert (
        result["details"]["registration_state"]
        == "Registered"
    )


@pytest.mark.parametrize(
    "registration_state",
    [
        "Rejected",
        "Unregistered",
        "Stopped",
    ],
)
def test_unproven_registration_states_fail_closed(
    registration_state,
):
    item = observation()

    item["registration"]["output"] = (
        " 555820_home/"
        "sip:provider.example:5060"
        " 555820_home "
        f"{registration_state}"
    )

    result = build_evidence(
        item,
        observed_at=OBSERVED_AT,
        now=NOW,
    )

    assert result["state"] == "UNKNOWN"
    assert result["reported_state"] == "UNKNOWN"
    assert (
        result["details"]["registration_state"]
        == registration_state
    )


def test_asterisk_probe_failure_is_unknown():
    item = observation()

    item["asterisk_cli"] = {
        "successful": False,
        "output": "",
    }

    result = build_evidence(
            item,
            observed_at=OBSERVED_AT,
            now=NOW,
        )

    assert result["state"] == "UNKNOWN"


def test_registration_probe_failure_is_unknown():
    item = observation()

    item["registration"] = {
        "id": "555820_home",
        "successful": False,
        "output": "",
    }

    result = build_evidence(
            item,
            observed_at=OBSERVED_AT,
            now=NOW,
        )

    assert result["state"] == "UNKNOWN"


def test_missing_registration_is_unknown():
    item = observation()

    item["registration"]["output"] = (
        "Objects found: 0"
    )

    result = build_evidence(
            item,
            observed_at=OBSERVED_AT,
            now=NOW,
        )

    assert result["state"] == "UNKNOWN"
    assert (
        result["details"]["registration_state"]
        is None
    )


def test_unrecognized_registration_state_is_unknown():
    item = observation()

    item["registration"]["output"] = (
        " 555820_home/"
        "sip:provider.example:5060"
        " 555820_home"
        " MysteryState"
    )

    result = build_evidence(
            item,
            observed_at=OBSERVED_AT,
            now=NOW,
        )

    assert result["state"] == "UNKNOWN"
    assert (
        result["details"]["registration_state"]
        == "MysteryState"
    )


def test_other_registration_cannot_satisfy_target():
    item = observation()

    item["registration"]["output"] = (
        " other_trunk/"
        "sip:provider.example:5060"
        " other_trunk"
        " Registered"
    )

    result = build_evidence(
            item,
            observed_at=OBSERVED_AT,
            now=NOW,
        )

    assert result["state"] == "UNKNOWN"


def test_stale_registered_evidence_fails_closed():
    result = build_evidence(
            observation(),
            observed_at=datetime(
            2026,
            9,
            20,
            6,
            40,
            0,
            tzinfo=UTC,        ),
            now=NOW,
        )

    assert result["reported_state"] == "AVAILABLE"
    assert result["state"] == "UNKNOWN"
    assert result["stale"] is True


def test_availability_bridge_accepts_result():
    from himp.services.functional_evidence import (
        FunctionalEvidenceService,
    )
    from himp.services.service_availability import (
        ServiceAvailabilityService,
    )

    normalized = build_evidence(
            observation(),
            observed_at=OBSERVED_AT,
            now=NOW,
        )

    provider = {
        "entity_type": normalized["entity_type"],
        "entity_id": normalized["entity_id"],
        "state": normalized["state"],
    }

    policy = {
        "service_type": "service",
        "service_id": "home_telephone",
        "display_name": "Home Telephone",
        "minimum_available": 1,
        "providers": [
            {
                "entity_type": "host",
                "entity_id": "freepbx",
            }
        ],
    }

    result = ServiceAvailabilityService.evaluate(
        policy,
        [provider],
    )

    assert result["state"] == "AVAILABLE"
    assert result["available_count"] == 1

    assert (
        FunctionalEvidenceService.AVAILABLE
        == normalized["reported_state"]
    )


def test_rejects_non_mapping_observation():
    with pytest.raises(
        ValueError,
        match="must be a mapping",
    ):
        build_evidence(
            [],
            observed_at=OBSERVED_AT,
            now=NOW,
        )


def test_core_validation_rejects_missing_freshness():
    item = observation()
    del item["fresh_for_seconds"]

    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        build_evidence(
            item,
            observed_at=OBSERVED_AT,
            now=NOW,
        )
