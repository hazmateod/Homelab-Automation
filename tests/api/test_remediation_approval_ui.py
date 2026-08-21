from fastapi.testclient import TestClient

from himp.api import server
from himp.api.dependencies import (
    require_page_session,
)


def authenticated_page_session():
    return {
        "username": "operator",
        "role": "operator",
    }


def empty_audit_history(
    limit=50,
    source_type=None,
    source_id=None,
    decision=None,
):
    return []


def audit_summary():
    return {
        "total": 0,
        "allow_count": 0,
        "deny_count": 0,
        "confirmation_required_count": 0,
        "execution_success_count": 0,
        "execution_failure_count": 0,
        "verification_success_count": 0,
        "verification_failure_count": 0,
        "verification_not_supported_count": 0,
    }


def approval(
    *,
    approval_id=7,
    status="PENDING",
):
    return {
        "id": approval_id,
        "recommendation_id":
            "HOST_UNHEALTHY:pve01",
        "source_type": "application",
        "source_id": "himp",
        "target_type": "host",
        "target_id": "pve01",
        "condition": "HOST_UNHEALTHY",
        "severity": "CRITICAL",
        "recommended_action":
            "Investigate host connectivity.",
        "rationale":
            "Persisted health evidence is unhealthy.",
        "evidence": {
            "current_status": "FAIL",
        },
        "affected_assets": [
            {
                "entity_type": "application",
                "entity_id": "himp",
            }
        ],
        "dependency_depth": 1,
        "dependency_path": [],
        "status": status,
        "requested_by": "admin",
        "decided_by": (
            "admin"
            if status != "PENDING"
            else None
        ),
        "decision_note": (
            "Reviewed."
            if status != "PENDING"
            else None
        ),
        "created_at":
            "2026-08-21 01:00:00",
        "decided_at": (
            "2026-08-21 01:05:00"
            if status != "PENDING"
            else None
        ),
    }


def configure_page(
    monkeypatch,
    *,
    approvals=None,
    summary=None,
    captured=None,
):
    monkeypatch.setattr(
        server.remediation_audit_repository,
        "history",
        empty_audit_history,
    )

    monkeypatch.setattr(
        server.remediation_audit_repository,
        "summary",
        audit_summary,
    )

    def fake_list(
        limit=100,
        status=None,
    ):
        if captured is not None:
            captured["limit"] = limit
            captured["status"] = status

        records = (
            approvals
            if approvals is not None
            else []
        )

        return {
            "count": len(records),
            "summary": (
                summary
                if summary is not None
                else {
                    "total": len(records),
                    "pending": sum(
                        item["status"] == "PENDING"
                        for item in records
                    ),
                    "approved": sum(
                        item["status"] == "APPROVED"
                        for item in records
                    ),
                    "denied": sum(
                        item["status"] == "DENIED"
                        for item in records
                    ),
                }
            ),
            "approvals": records,
        }

    monkeypatch.setattr(
        server.remediation_approval_service,
        "list",
        fake_list,
    )

    monkeypatch.setattr(
        server.remediation_scheduling_service,
        "list",
        lambda limit=100, status=None: {
            "count": 0,
            "summary": {
                "total": 0,
                "scheduled": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0,
            },
            "schedules": [],
        },
    )


def test_remediation_page_renders_approval_queue(
    monkeypatch,
):
    configure_page(
        monkeypatch,
        approvals=[
            approval()
        ],
    )

    server.app.dependency_overrides[
        require_page_session
    ] = authenticated_page_session

    try:
        with TestClient(server.app) as client:
            response = client.get(
                "/remediation"
            )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "Approval Queue" in response.text
    assert "pve01" in response.text
    assert "HOST_UNHEALTHY" in response.text
    assert "CRITICAL" in response.text
    assert "PENDING" in response.text

    assert (
        "Investigate host connectivity."
        in response.text
    )

    assert (
        "it does not execute remediation."
        in response.text
    )


def test_pending_approval_renders_decision_controls(
    monkeypatch,
):
    configure_page(
        monkeypatch,
        approvals=[
            approval()
        ],
    )

    server.app.dependency_overrides[
        require_page_session
    ] = authenticated_page_session

    try:
        with TestClient(server.app) as client:
            response = client.get(
                "/remediation"
            )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "Approve" in response.text
    assert "Deny" in response.text

    assert (
        "remediation-approval-approve"
        in response.text
    )

    assert (
        "remediation-approval-deny"
        in response.text
    )

    assert (
        "Administrator authorization required."
        in response.text
    )


def test_decided_approval_does_not_render_action_group(
    monkeypatch,
):
    configure_page(
        monkeypatch,
        approvals=[
            approval(
                status="APPROVED"
            )
        ],
    )

    server.app.dependency_overrides[
        require_page_session
    ] = authenticated_page_session

    try:
        with TestClient(server.app) as client:
            response = client.get(
                "/remediation"
            )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "APPROVED" in response.text
    assert "Decision recorded." in response.text

    assert (
        "remediation-approval-actions"
        not in response.text
    )

    assert (
        'data-approval-id="7"'
        in response.text
    )

    assert (
        "remediation-schedule-create"
        in response.text
    )


def test_remediation_page_passes_approval_filter(
    monkeypatch,
):
    captured = {}

    configure_page(
        monkeypatch,
        approvals=[],
        captured=captured,
    )

    server.app.dependency_overrides[
        require_page_session
    ] = authenticated_page_session

    try:
        with TestClient(server.app) as client:
            response = client.get(
                "/remediation",
                params={
                    "approval_status":
                        "APPROVED",
                },
            )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200

    assert captured == {
        "limit": 100,
        "status": "APPROVED",
    }

    assert (
        "All Approval States"
        in response.text
    )


def test_invalid_approval_filter_fails_safe_to_all(
    monkeypatch,
):
    captured = {}

    configure_page(
        monkeypatch,
        approvals=[],
        captured=captured,
    )

    server.app.dependency_overrides[
        require_page_session
    ] = authenticated_page_session

    try:
        with TestClient(server.app) as client:
            response = client.get(
                "/remediation",
                params={
                    "approval_status":
                        "EXECUTED",
                },
            )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200

    assert captured == {
        "limit": 100,
        "status": None,
    }
