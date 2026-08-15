import pytest

from himp.services.remediation_proposals import (
    RemediationProposalService,
)


def intelligence(
    relationships=None,
    changes=None,
    drift=None,
):
    return {
        "source_type": "host",
        "source_id": "pve01",
        "relationships": relationships or [],
        "changes": changes or [],
        "drift": drift or [],
    }


class FakeIntelligence:
    def __init__(
        self,
        result,
    ):
        self.result = result
        self.calls = []

    def inspect(
        self,
        source_type,
        source_id,
        baseline=None,
        change_limit=10,
    ):
        self.calls.append(
            {
                "source_type": source_type,
                "source_id": source_id,
                "baseline": baseline,
                "change_limit": change_limit,
            }
        )

        return self.result


def make_service(
    result,
):
    intelligence_service = FakeIntelligence(
        result
    )

    service = RemediationProposalService(
        intelligence=intelligence_service,
    )

    return (
        service,
        intelligence_service,
    )


def test_failed_related_host_creates_remediation_proposal():
    service, intelligence_service = make_service(
        intelligence(
            relationships=[
                {
                    "source_type": "host",
                    "source_id": "pve01",
                    "relationship_type": "depends_on",
                    "target_type": "host",
                    "target_id": "pve02",
                    "health_status": "FAIL",
                },
            ],
        )
    )

    result = service.propose(
        source_type="host",
        source_id="pve01",
    )

    assert result["proposals"] == [
        {
            "task_id": "scheduled_updates",
            "reason": (
                "Related host pve02 has failed health."
            ),
            "evidence": {
                "source_type": "host",
                "source_id": "pve01",
                "target_type": "host",
                "target_id": "pve02",
                "health_status": "FAIL",
            },
        }
    ]

    assert intelligence_service.calls == [
        {
            "source_type": "host",
            "source_id": "pve01",
            "baseline": None,
            "change_limit": 10,
        }
    ]


def test_warning_related_host_creates_remediation_proposal():
    service, _ = make_service(
        intelligence(
            relationships=[
                {
                    "source_type": "host",
                    "source_id": "pve01",
                    "relationship_type": "depends_on",
                    "target_type": "host",
                    "target_id": "pve02",
                    "health_status": "WARNING",
                },
            ],
        )
    )

    result = service.propose(
        source_type="host",
        source_id="pve01",
    )

    assert len(result["proposals"]) == 1
    assert result["proposals"][0]["task_id"] == (
        "scheduled_updates"
    )


def test_inventory_drift_creates_remediation_proposal():
    service, _ = make_service(
        intelligence(
            drift=[
                {
                    "hostname": "pve01",
                    "field": "ip",
                    "expected": "192.168.10.51",
                    "actual": "192.168.10.52",
                    "drift_type": "CHANGED",
                },
            ],
        )
    )

    result = service.propose(
        source_type="host",
        source_id="pve01",
        baseline="production",
    )

    assert result["proposals"] == [
        {
            "task_id": "scheduled_updates",
            "reason": (
                "Inventory baseline drift detected for pve01."
            ),
            "evidence": {
                "baseline": "production",
                "drift": [
                    {
                        "hostname": "pve01",
                        "field": "ip",
                        "expected": "192.168.10.51",
                        "actual": "192.168.10.52",
                        "drift_type": "CHANGED",
                    },
                ],
            },
        }
    ]


def test_clean_intelligence_produces_no_proposals():
    service, _ = make_service(
        intelligence()
    )

    result = service.propose(
        source_type="host",
        source_id="pve01",
    )

    assert result == {
        "source_type": "host",
        "source_id": "pve01",
        "proposals": [],
    }


def test_unknown_health_does_not_create_proposal():
    service, _ = make_service(
        intelligence(
            relationships=[
                {
                    "source_type": "host",
                    "source_id": "pve01",
                    "relationship_type": "depends_on",
                    "target_type": "host",
                    "target_id": "pve02",
                    "health_status": "UNKNOWN",
                },
            ],
        )
    )

    result = service.propose(
        source_type="host",
        source_id="pve01",
    )

    assert result["proposals"] == []


def test_proposal_generation_does_not_execute_automation():
    service, _ = make_service(
        intelligence(
            relationships=[
                {
                    "source_type": "host",
                    "source_id": "pve01",
                    "relationship_type": "depends_on",
                    "target_type": "host",
                    "target_id": "pve02",
                    "health_status": "FAIL",
                },
            ],
        )
    )

    result = service.propose(
        source_type="host",
        source_id="pve01",
    )

    assert result["proposals"]
