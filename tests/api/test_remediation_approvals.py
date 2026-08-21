from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from himp.api import remediation


class FakeApprovalService:
    def __init__(self):
        self.enqueue_calls = []
        self.list_calls = []
        self.get_calls = []
        self.approve_calls = []
        self.deny_calls = []

    def enqueue(
        self,
        entity_type,
        entity_id,
        recommendation_id,
        requested_by,
        limit=100,
    ):
        self.enqueue_calls.append(
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "recommendation_id": (
                    recommendation_id
                ),
                "requested_by": requested_by,
                "limit": limit,
            }
        )

        return {
            "id": 1,
            "status": "PENDING",
        }

    def list(
        self,
        limit=100,
        status=None,
    ):
        self.list_calls.append(
            {
                "limit": limit,
                "status": status,
            }
        )

        return {
            "count": 0,
            "summary": {
                "total": 0,
                "pending": 0,
                "approved": 0,
                "denied": 0,
            },
            "approvals": [],
        }

    def get(
        self,
        approval_id,
    ):
        self.get_calls.append(
            approval_id
        )

        if approval_id == 404:
            raise KeyError(
                "approval does not exist"
            )

        return {
            "id": approval_id,
            "status": "PENDING",
        }

    def approve(
        self,
        approval_id,
        decided_by,
        decision_note=None,
    ):
        self.approve_calls.append(
            {
                "approval_id": approval_id,
                "decided_by": decided_by,
                "decision_note": decision_note,
            }
        )

        return {
            "id": approval_id,
            "status": "APPROVED",
        }

    def deny(
        self,
        approval_id,
        decided_by,
        decision_note=None,
    ):
        self.deny_calls.append(
            {
                "approval_id": approval_id,
                "decided_by": decided_by,
                "decision_note": decision_note,
            }
        )

        return {
            "id": approval_id,
            "status": "DENIED",
        }


@pytest.fixture
def fake_service():
    original = (
        remediation.remediation_approval_service
    )

    fake = FakeApprovalService()

    remediation.remediation_approval_service = (
        fake
    )

    yield fake

    remediation.remediation_approval_service = (
        original
    )


def admin():
    return SimpleNamespace(
        username="admin",
        role="admin",
    )


def test_create_approval_uses_admin_identity(
    fake_service,
):
    request = (
        remediation.RemediationApprovalCreateRequest(
            entity_type="application",
            entity_id="himp",
            recommendation_id=(
                "HOST_UNHEALTHY:pve01"
            ),
            limit=25,
        )
    )

    result = (
        remediation.create_remediation_approval(
            request=request,
            admin=admin(),
        )
    )

    assert result["status"] == "PENDING"

    assert fake_service.enqueue_calls == [
        {
            "entity_type": "application",
            "entity_id": "himp",
            "recommendation_id": (
                "HOST_UNHEALTHY:pve01"
            ),
            "requested_by": "admin",
            "limit": 25,
        }
    ]


def test_list_approvals_delegates(
    fake_service,
):
    result = (
        remediation.remediation_approval_queue(
            limit=20,
            status="PENDING",
        )
    )

    assert result["count"] == 0

    assert fake_service.list_calls == [
        {
            "limit": 20,
            "status": "PENDING",
        }
    ]


def test_get_missing_approval_returns_404(
    fake_service,
):
    with pytest.raises(
        HTTPException
    ) as error:
        remediation.remediation_approval_detail(
            approval_id=404
        )

    assert error.value.status_code == 404


def test_approve_records_admin_identity(
    fake_service,
):
    request = (
        remediation.RemediationApprovalDecisionRequest(
            note="Reviewed.",
        )
    )

    result = remediation.approve_remediation(
        approval_id=7,
        request=request,
        admin=admin(),
    )

    assert result["status"] == "APPROVED"

    assert fake_service.approve_calls == [
        {
            "approval_id": 7,
            "decided_by": "admin",
            "decision_note": "Reviewed.",
        }
    ]


def test_deny_records_admin_identity(
    fake_service,
):
    request = (
        remediation.RemediationApprovalDecisionRequest(
            note="Denied.",
        )
    )

    result = remediation.deny_remediation(
        approval_id=7,
        request=request,
        admin=admin(),
    )

    assert result["status"] == "DENIED"

    assert fake_service.deny_calls == [
        {
            "approval_id": 7,
            "decided_by": "admin",
            "decision_note": "Denied.",
        }
    ]


def test_approval_routes_are_registered():
    from himp.api.server import app

    schema = app.openapi()
    paths = schema["paths"]

    required = {
        "/api/remediation/approvals": {
            "get",
            "post",
        },
        "/api/remediation/approvals/{approval_id}": {
            "get",
        },
        (
            "/api/remediation/approvals/"
            "{approval_id}/approve"
        ): {
            "post",
        },
        (
            "/api/remediation/approvals/"
            "{approval_id}/deny"
        ): {
            "post",
        },
    }

    for path, methods in required.items():
        assert path in paths
        assert methods.issubset(
            set(paths[path])
        )
