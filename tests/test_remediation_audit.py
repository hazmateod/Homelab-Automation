import pytest

from himp.services.remediation_audit import (
    RemediationAuditService,
)


class FakeRepository:
    def __init__(self):
        self.records = []
        self.next_id = 1

    def save(
        self,
        source_type,
        source_id,
        task_id,
        decision,
        reason,
        evidence,
        risk_level,
        confirmation_required,
        confirmed,
        execution_id=None,
        execution_success=None,
        verification_status=None,
        verification_success=None,
        verification_evidence=None,
    ):
        record = {
            "id": self.next_id,
            "source_type": source_type,
            "source_id": source_id,
            "task_id": task_id,
            "decision": decision,
            "reason": reason,
            "evidence": evidence,
            "risk_level": risk_level,
            "confirmation_required": confirmation_required,
            "confirmed": confirmed,
            "execution_id": execution_id,
            "execution_success": execution_success,
            "verification_status": verification_status,
            "verification_success": verification_success,
            "verification_evidence": verification_evidence,
        }

        self.next_id += 1
        self.records.append(record)

        return record


def make_service():
    repository = FakeRepository()

    return (
        RemediationAuditService(
            repository=repository,
        ),
        repository,
    )


def proposal():
    return {
        "task_id": "scheduled_updates",
        "reason": (
            "Host health indicates maintenance is required."
        ),
        "evidence": {
            "hostname": "pve01",
            "status": "WARNING",
        },
    }


def allowed_result():
    return {
        "decision": "ALLOW",
        "policy": {
            "decision": "ALLOW",
            "task_id": "scheduled_updates",
            "reason": (
                "Host health indicates maintenance is required."
            ),
            "evidence": {
                "hostname": "pve01",
                "status": "WARNING",
            },
            "risk_level": "maintenance",
            "confirmation_required": False,
        },
        "execution": {
            "id": 42,
            "task": "scheduled_updates",
            "success": True,
        },
    }


def denied_result():
    return {
        "decision": "DENY",
        "policy": {
            "decision": "DENY",
            "task_id": "scheduled_updates",
            "reason": "automation disabled",
            "evidence": {
                "hostname": "pve01",
                "status": "WARNING",
            },
            "risk_level": "maintenance",
            "confirmation_required": False,
        },
    }


def confirmation_result():
    return {
        "decision": "CONFIRM_REQUIRED",
        "policy": {
            "decision": "CONFIRM_REQUIRED",
            "task_id": "scheduled_updates",
            "reason": (
                "Destructive remediation requires confirmation."
            ),
            "evidence": {
                "hostname": "pve01",
                "status": "WARNING",
            },
            "risk_level": "destructive",
            "confirmation_required": True,
        },
    }


def test_allowed_remediation_is_audited_with_execution_reference():
    service, repository = make_service()

    result = service.record(
        source_type="host",
        source_id="pve01",
        proposal=proposal(),
        remediation=allowed_result(),
        confirmed=False,
    )

    assert result["id"] == 1
    assert result["decision"] == "ALLOW"
    assert result["task_id"] == "scheduled_updates"
    assert result["execution_id"] == 42
    assert result["execution_success"] is True

    assert repository.records == [
        result
    ]


def test_denied_remediation_is_audited_without_execution():
    service, repository = make_service()

    result = service.record(
        source_type="host",
        source_id="pve01",
        proposal=proposal(),
        remediation=denied_result(),
        confirmed=False,
    )

    assert result["decision"] == "DENY"
    assert result["execution_id"] is None
    assert result["execution_success"] is None

    assert repository.records == [
        result
    ]


def test_confirmation_required_is_audited_without_execution():
    service, repository = make_service()

    result = service.record(
        source_type="host",
        source_id="pve01",
        proposal=proposal(),
        remediation=confirmation_result(),
        confirmed=False,
    )

    assert result["decision"] == "CONFIRM_REQUIRED"
    assert result["confirmation_required"] is True
    assert result["execution_id"] is None
    assert result["execution_success"] is None

    assert repository.records == [
        result
    ]


def test_confirmed_execution_records_confirmation():
    service, repository = make_service()

    result = service.record(
        source_type="host",
        source_id="pve01",
        proposal=proposal(),
        remediation=allowed_result(),
        confirmed=True,
    )

    assert result["decision"] == "ALLOW"
    assert result["confirmed"] is True
    assert result["execution_id"] == 42

    assert repository.records[0]["confirmed"] is True


def test_audit_preserves_proposal_evidence():
    service, repository = make_service()

    result = service.record(
        source_type="host",
        source_id="pve01",
        proposal=proposal(),
        remediation=allowed_result(),
    )

    assert result["evidence"] == {
        "hostname": "pve01",
        "status": "WARNING",
    }


def test_audit_requires_source_identity():
    service, _ = make_service()

    with pytest.raises(
        ValueError,
        match="source_type",
    ):
        service.record(
            source_type="",
            source_id="pve01",
            proposal=proposal(),
            remediation=allowed_result(),
        )


def test_audit_requires_task_id():
    service, _ = make_service()

    invalid = proposal()
    invalid["task_id"] = ""

    with pytest.raises(
        ValueError,
        match="task_id",
    ):
        service.record(
            source_type="host",
            source_id="pve01",
            proposal=invalid,
            remediation=allowed_result(),
        )


def test_audit_persists_verification_independently_from_execution():
    service, repository = make_service()

    remediation = allowed_result()

    remediation["verification"] = {
        "status": "NOT_VERIFIED",
        "success": False,
        "condition": "HOST_UNHEALTHY",
        "reason": (
            "Fresh health still failed."
        ),
        "evidence": {
            "fresh_health": {
                "hostname": "pve01",
            }
        },
    }

    result = service.record(
        source_type="host",
        source_id="pve01",
        proposal=proposal(),
        remediation=remediation,
        confirmed=True,
    )

    assert result[
        "execution_success"
    ] is True

    assert result[
        "verification_status"
    ] == "NOT_VERIFIED"

    assert result[
        "verification_success"
    ] is False

    assert result[
        "verification_evidence"
    ] == remediation["verification"]

    assert repository.records == [
        result
    ]
