import pytest

from himp.services.remediation_approvals import (
    RemediationApprovalService,
)


def recommendation():
    return {
        "recommendation_id": (
            "HOST_UNHEALTHY:pve01"
        ),
        "condition": "HOST_UNHEALTHY",
        "severity": "CRITICAL",
        "target": {
            "entity_type": "host",
            "entity_id": "pve01",
        },
        "dependency_depth": 1,
        "dependency_path": [],
        "evidence": {
            "current_state": "UNHEALTHY",
        },
        "affected_assets": [],
        "recommended_action": "Investigate.",
        "rationale": "Health evidence.",
        "automation": None,
        "execution_permitted": False,
    }


class FakeRepository:
    def __init__(self):
        self.created = []
        self.decisions = []
        self.records = {}

    def create(
        self,
        recommendation,
        source_type,
        source_id,
        requested_by,
    ):
        self.created.append(
            {
                "recommendation": recommendation,
                "source_type": source_type,
                "source_id": source_id,
                "requested_by": requested_by,
            }
        )

        result = {
            "id": 1,
            "status": "PENDING",
            "recommendation_id": (
                recommendation[
                    "recommendation_id"
                ]
            ),
        }

        self.records[1] = result
        return result

    def list(
        self,
        limit=100,
        status=None,
    ):
        return list(
            self.records.values()
        )

    def summary(self):
        return {
            "total": len(self.records),
            "pending": len(self.records),
            "approved": 0,
            "denied": 0,
        }

    def find(self, approval_id):
        return self.records.get(
            approval_id
        )

    def decide(
        self,
        approval_id,
        status,
        decided_by,
        decision_note=None,
    ):
        self.decisions.append(
            {
                "approval_id": approval_id,
                "status": status,
                "decided_by": decided_by,
                "decision_note": decision_note,
            }
        )

        record = {
            "id": approval_id,
            "status": status,
            "decided_by": decided_by,
            "decision_note": decision_note,
        }

        self.records[
            approval_id
        ] = record

        return record


class FakeRecommendations:
    def __init__(
        self,
        recommendations=None,
    ):
        self.items = (
            recommendations
            if recommendations is not None
            else [recommendation()]
        )
        self.calls = []

    def recommend(
        self,
        entity_type,
        entity_id,
        limit=100,
    ):
        self.calls.append(
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "limit": limit,
            }
        )

        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "recommendation_count": len(
                self.items
            ),
            "execution_performed": False,
            "recommendations": self.items,
        }


def make_service(
    recommendations=None,
):
    repository = FakeRepository()
    recommendation_service = (
        FakeRecommendations(
            recommendations=recommendations
        )
    )

    service = RemediationApprovalService(
        repository=repository,
        recommendations=recommendation_service,
    )

    return (
        service,
        repository,
        recommendation_service,
    )


def test_enqueue_requires_current_recommendation():
    service, repository, _ = make_service(
        recommendations=[]
    )

    with pytest.raises(
        ValueError,
        match="currently supported",
    ):
        service.enqueue(
            entity_type="application",
            entity_id="himp",
            recommendation_id=(
                "HOST_UNHEALTHY:pve01"
            ),
            requested_by="admin",
        )

    assert repository.created == []


def test_enqueue_regenerates_current_evidence():
    service, repository, recommendations = (
        make_service()
    )

    result = service.enqueue(
        entity_type="application",
        entity_id="himp",
        recommendation_id=(
            "HOST_UNHEALTHY:pve01"
        ),
        requested_by="admin",
        limit=25,
    )

    assert result["status"] == "PENDING"

    assert recommendations.calls == [
        {
            "entity_type": "application",
            "entity_id": "himp",
            "limit": 25,
        }
    ]

    assert repository.created[0][
        "requested_by"
    ] == "admin"


def test_list_returns_summary_and_records():
    service, repository, _ = make_service()

    repository.records[1] = {
        "id": 1,
        "status": "PENDING",
    }

    result = service.list()

    assert result["count"] == 1
    assert result["summary"]["pending"] == 1


def test_get_missing_approval_fails():
    service, _, _ = make_service()

    with pytest.raises(
        KeyError,
        match="does not exist",
    ):
        service.get(42)


def test_approve_delegates_without_execution():
    service, repository, _ = make_service()

    result = service.approve(
        approval_id=3,
        decided_by="admin",
        decision_note="Approved.",
    )

    assert result["status"] == "APPROVED"
    assert repository.decisions == [
        {
            "approval_id": 3,
            "status": "APPROVED",
            "decided_by": "admin",
            "decision_note": "Approved.",
        }
    ]


def test_deny_delegates_without_execution():
    service, repository, _ = make_service()

    result = service.deny(
        approval_id=3,
        decided_by="admin",
        decision_note="Denied.",
    )

    assert result["status"] == "DENIED"
    assert repository.decisions[0][
        "status"
    ] == "DENIED"
