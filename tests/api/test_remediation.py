import pytest

from fastapi import HTTPException

from himp.api import remediation


class FakeWorkflowService:
    def __init__(self, result=None):
        self.result = result or {
            "source_type": "host",
            "source_id": "pve01",
            "baseline": "production",
            "proposal_count": 1,
            "executed_count": 1,
            "blocked_count": 0,
            "results": [
                {
                    "decision": "ALLOW",
                    "execution": {
                        "id": 42,
                        "success": True,
                    },
                }
            ],
        }
        self.calls = []

    def run(
        self,
        source_type,
        source_id,
        baseline=None,
        change_limit=10,
        confirmed=False,
    ):
        self.calls.append(
            {
                "source_type": source_type,
                "source_id": source_id,
                "baseline": baseline,
                "change_limit": change_limit,
                "confirmed": confirmed,
            }
        )
        return self.result


class FakeProposalService:
    def __init__(self, result=None):
        self.result = result or {
            "source_type": "host",
            "source_id": "pve01",
            "proposals": [
                {
                    "task_id": "scheduled_updates",
                    "reason": "Maintenance required.",
                    "evidence": {
                        "hostname": "pve01",
                    },
                }
            ],
        }
        self.calls = []

    def propose(
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


class FakeAuditRepository:
    def __init__(self, records=None):
        self.records = records or []
        self.calls = []

    def history(
        self,
        limit=50,
        source_type=None,
        source_id=None,
        decision=None,
    ):
        self.calls.append(
            {
                "limit": limit,
                "source_type": source_type,
                "source_id": source_id,
                "decision": decision,
            }
        )

        return self.records


def test_run_remediation_delegates_to_workflow():
    workflow = FakeWorkflowService()

    original = remediation.remediation_workflow_service
    remediation.remediation_workflow_service = workflow

    try:
        result = remediation.run_remediation(
            remediation.RemediationRunRequest(
                source_type="host",
                source_id="pve01",
                baseline="production",
                change_limit=5,
                confirmed=True,
            )
        )
    finally:
        remediation.remediation_workflow_service = original

    assert result == workflow.result

    assert workflow.calls == [
        {
            "source_type": "host",
            "source_id": "pve01",
            "baseline": "production",
            "change_limit": 5,
            "confirmed": True,
        }
    ]


def test_generate_proposals_delegates_to_proposal_service():
    proposals = FakeProposalService()

    original = remediation.remediation_proposal_service
    remediation.remediation_proposal_service = proposals

    try:
        result = remediation.generate_remediation_proposals(
            remediation.RemediationProposalRequest(
                source_type="host",
                source_id="pve01",
                baseline="production",
                change_limit=7,
            )
        )
    finally:
        remediation.remediation_proposal_service = original

    assert result == proposals.result

    assert proposals.calls == [
        {
            "source_type": "host",
            "source_id": "pve01",
            "baseline": "production",
            "change_limit": 7,
        }
    ]


def test_audit_history_delegates_to_repository():
    repository = FakeAuditRepository(
        records=[
            {
                "id": 1,
                "source_type": "host",
                "source_id": "pve01",
                "decision": "ALLOW",
            }
        ]
    )

    original = remediation.remediation_audit_repository
    remediation.remediation_audit_repository = repository

    try:
        result = remediation.remediation_audit_history(
            limit=25,
            source_type="host",
            source_id="pve01",
            decision="ALLOW",
        )
    finally:
        remediation.remediation_audit_repository = original

    assert result == {
        "count": 1,
        "history": repository.records,
    }

    assert repository.calls == [
        {
            "limit": 25,
            "source_type": "host",
            "source_id": "pve01",
            "decision": "ALLOW",
        }
    ]


def test_run_request_defaults_are_safe():
    request = remediation.RemediationRunRequest(
        source_type="host",
        source_id="pve01",
    )

    assert request.baseline is None
    assert request.change_limit == 10
    assert request.confirmed is False


def test_proposal_request_defaults_are_deterministic():
    request = remediation.RemediationProposalRequest(
        source_type="host",
        source_id="pve01",
    )

    assert request.baseline is None
    assert request.change_limit == 10


def test_audit_limit_is_constrained():
    with pytest.raises(Exception):
        remediation.remediation_audit_history(
            limit=0
        )


def test_remediation_run_requires_source_type():
    with pytest.raises(Exception):
        remediation.RemediationRunRequest(
            source_type="",
            source_id="pve01",
        )


def test_remediation_run_requires_source_id():
    with pytest.raises(Exception):
        remediation.RemediationRunRequest(
            source_type="host",
            source_id="",
        )


def test_remediation_routes_require_session():
    from fastapi.testclient import TestClient
    from himp.api import server

    with TestClient(server.app) as client:
        proposals = client.post(
            "/api/remediation/proposals",
            json={
                "source_type": "host",
                "source_id": "pve01",
            },
        )

        run = client.post(
            "/api/remediation/run",
            json={
                "source_type": "host",
                "source_id": "pve01",
            },
        )

        audit = client.get(
            "/api/remediation/audit"
        )

    assert proposals.status_code == 401
    assert proposals.json() == {
        "detail": "Authentication required"
    }

    assert run.status_code == 401
    assert run.json() == {
        "detail": "Authentication required"
    }

    assert audit.status_code == 401
    assert audit.json() == {
        "detail": "Authentication required"
    }


def test_remediation_routes_are_registered():
    from himp.api import server

    paths = set(
        server.app.openapi()["paths"]
    )

    assert "/api/remediation/proposals" in paths
    assert "/api/remediation/run" in paths
    assert "/api/remediation/audit" in paths
