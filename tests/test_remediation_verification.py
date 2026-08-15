import pytest

from himp.services.remediation_verification import (
    RemediationVerificationService,
)


class FakeHealthService:
    def __init__(
        self,
        status="PASS",
    ):
        self.status = status
        self.calls = []

    def check_host(
        self,
        hostname,
    ):
        self.calls.append(hostname)

        return {
            "hostname": hostname,
            "results": [
                {
                    "status": self.status,
                }
            ],
        }


def allowed_remediation():
    return {
        "decision": "ALLOW",
        "execution": {
            "id": 42,
            "success": True,
        },
    }


def denied_remediation():
    return {
        "decision": "DENY",
        "policy": {
            "decision": "DENY",
        },
    }


def host_proposal():
    return {
        "task_id": "scheduled_updates",
        "reason": "Related host pve02 has failed health.",
        "evidence": {
            "source_type": "host",
            "source_id": "pve01",
            "target_type": "host",
            "target_id": "pve02",
            "health_status": "FAIL",
        },
    }


def make_service(
    status="PASS",
):
    health = FakeHealthService(
        status=status
    )

    service = RemediationVerificationService(
        health=health,
    )

    return service, health


def test_successful_remediation_with_healthy_host_is_verified():
    service, health = make_service()

    result = service.verify(
        proposal=host_proposal(),
        remediation=allowed_remediation(),
    )

    assert result["status"] == "VERIFIED"
    assert result["success"] is True
    assert result["hostname"] == "pve02"
    assert health.calls == ["pve02"]


def test_successful_remediation_with_failed_host_fails_verification():
    service, health = make_service(
        status="FAIL"
    )

    result = service.verify(
        proposal=host_proposal(),
        remediation=allowed_remediation(),
    )

    assert result["status"] == "FAILED"
    assert result["success"] is False
    assert result["hostname"] == "pve02"
    assert health.calls == ["pve02"]


def test_denied_remediation_is_not_verified():
    service, health = make_service()

    result = service.verify(
        proposal=host_proposal(),
        remediation=denied_remediation(),
    )

    assert result == {
        "status": "NOT_EXECUTED",
        "success": False,
    }

    assert health.calls == []
