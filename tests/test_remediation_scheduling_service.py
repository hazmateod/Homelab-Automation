from datetime import datetime, timedelta

import pytest

from himp.services.remediation_scheduling import (
    RemediationSchedulingService,
)


def approved_record(
    *,
    approval_id=7,
    status="APPROVED",
):
    return {
        "id": approval_id,
        "recommendation_id":
            "HOST_UNHEALTHY:pve01",
        "task_id": "scheduled_updates",
        "source_type": "application",
        "source_id": "himp",
        "target_type": "host",
        "target_id": "pve01",
        "condition": "HOST_UNHEALTHY",
        "severity": "CRITICAL",
        "recommended_action": "Investigate.",
        "rationale": "Approved evidence.",
        "evidence": {
            "current_status": "FAIL",
        },
        "affected_assets": [],
        "dependency_depth": 1,
        "dependency_path": [],
        "status": status,
        "requested_by": "operator",
        "decided_by": "admin",
        "decision_note": "Approved.",
        "created_at": datetime.now(),
        "decided_at": datetime.now(),
    }


class FakeApprovals:
    def __init__(
        self,
        record=None,
    ):
        self.record = (
            record
            if record is not None
            else approved_record()
        )

    def find(self, approval_id):
        if (
            self.record is None
            or self.record["id"] != approval_id
        ):
            return None

        return self.record


class FakeRepository:
    def __init__(self):
        self.records = {}
        self.next_id = 1
        self.claimed = set()
        self.completed = []
        self.failed = []
        self.cancelled = []

    def find_by_approval(
        self,
        approval_id,
    ):
        for record in self.records.values():
            if record["approval_id"] == approval_id:
                return record

        return None

    def create(
        self,
        approval_id,
        scheduled_for,
        scheduled_by,
    ):
        record = {
            "id": self.next_id,
            "approval_id": approval_id,
            "scheduled_for": scheduled_for,
            "scheduled_by": scheduled_by,
            "status": "SCHEDULED",
        }

        self.records[
            self.next_id
        ] = record

        self.next_id += 1
        return record

    def find(self, schedule_id):
        return self.records.get(
            schedule_id
        )

    def list(
        self,
        limit=100,
        status=None,
    ):
        records = list(
            self.records.values()
        )

        if status is not None:
            records = [
                record
                for record in records
                if record["status"] == status
            ]

        return records[:limit]

    def summary(self):
        return {
            "total": len(self.records),
            "scheduled": sum(
                item["status"] == "SCHEDULED"
                for item in self.records.values()
            ),
            "running": sum(
                item["status"] == "RUNNING"
                for item in self.records.values()
            ),
            "completed": sum(
                item["status"] == "COMPLETED"
                for item in self.records.values()
            ),
            "failed": sum(
                item["status"] == "FAILED"
                for item in self.records.values()
            ),
            "cancelled": sum(
                item["status"] == "CANCELLED"
                for item in self.records.values()
            ),
        }

    def due(
        self,
        now=None,
        limit=100,
    ):
        return [
            item
            for item in self.records.values()
            if item["status"] == "SCHEDULED"
            and item["scheduled_for"] <= now
        ][:limit]

    def claim(
        self,
        schedule_id,
        now=None,
    ):
        record = self.records.get(
            schedule_id
        )

        if (
            record is None
            or record["status"] != "SCHEDULED"
            or record["scheduled_for"] > now
        ):
            return None

        record["status"] = "RUNNING"
        self.claimed.add(
            schedule_id
        )

        return record

    def complete(
        self,
        schedule_id,
        audit_id=None,
    ):
        record = self.records[
            schedule_id
        ]

        record["status"] = "COMPLETED"
        record["audit_id"] = audit_id

        self.completed.append(
            schedule_id
        )

        return record

    def fail(
        self,
        schedule_id,
        error,
        audit_id=None,
    ):
        record = self.records[
            schedule_id
        ]

        record["status"] = "FAILED"
        record["error"] = str(error)
        record["audit_id"] = audit_id

        self.failed.append(
            schedule_id
        )

        return record

    def cancel(
        self,
        schedule_id,
        cancelled_by,
        cancellation_note=None,
    ):
        record = self.records[
            schedule_id
        ]

        record["status"] = "CANCELLED"
        record["cancelled_by"] = cancelled_by
        record["cancellation_note"] = (
            cancellation_note
        )

        self.cancelled.append(
            schedule_id
        )

        return record


class FakeExecution:
    def __init__(
        self,
        decision="ALLOW",
        success=True,
    ):
        self.decision = decision
        self.success = success
        self.calls = []

    def execute(
        self,
        proposal,
        confirmed=False,
    ):
        self.calls.append(
            {
                "proposal": proposal,
                "confirmed": confirmed,
            }
        )

        result = {
            "decision": self.decision,
            "policy": {
                "decision": self.decision,
                "reason": proposal["reason"],
                "evidence": proposal["evidence"],
                "risk_level": "HIGH",
                "confirmation_required": True,
            },
        }

        if self.decision == "ALLOW":
            result["execution"] = {
                "id": 99,
                "success": self.success,
            }

        return result


class FakeVerification:
    def __init__(self):
        self.calls = []

    def verify(
        self,
        proposal,
        remediation,
    ):
        self.calls.append(
            proposal
        )

        return {
            "status": "VERIFIED",
            "success": True,
        }


class FakeAudit:
    def __init__(self):
        self.calls = []

    def record(
        self,
        source_type,
        source_id,
        proposal,
        remediation,
        confirmed=False,
    ):
        self.calls.append(
            {
                "source_type": source_type,
                "source_id": source_id,
                "proposal": proposal,
                "remediation": remediation,
                "confirmed": confirmed,
            }
        )

        return {
            "id": 55,
        }


def make_service(
    *,
    approval=None,
    execution=None,
):
    repository = FakeRepository()

    service = RemediationSchedulingService(
        repository=repository,
        approvals=FakeApprovals(
            approval
            if approval is not None
            else approved_record()
        ),
        execution=(
            execution
            if execution is not None
            else FakeExecution()
        ),
        verification=FakeVerification(),
        audit=FakeAudit(),
    )

    return service, repository


def test_only_approved_remediation_can_be_scheduled():
    service, _ = make_service(
        approval=approved_record(
            status="PENDING"
        )
    )

    with pytest.raises(
        ValueError,
        match="only an approved remediation",
    ):
        service.schedule(
            approval_id=7,
            scheduled_for=(
                datetime.now()
                + timedelta(hours=1)
            ),
            scheduled_by="admin",
        )


def test_schedule_requires_future_time():
    service, _ = make_service()

    with pytest.raises(
        ValueError,
        match="must be in the future",
    ):
        service.schedule(
            approval_id=7,
            scheduled_for=(
                datetime.now()
                - timedelta(minutes=1)
            ),
            scheduled_by="admin",
        )


def test_approval_can_have_only_one_schedule():
    service, _ = make_service()

    when = (
        datetime.now()
        + timedelta(hours=1)
    )

    service.schedule(
        approval_id=7,
        scheduled_for=when,
        scheduled_by="admin",
    )

    with pytest.raises(
        ValueError,
        match="already has",
    ):
        service.schedule(
            approval_id=7,
            scheduled_for=(
                when + timedelta(hours=1)
            ),
            scheduled_by="admin",
        )


def test_approved_snapshot_reconstructs_exact_task():
    proposal = (
        RemediationSchedulingService
        ._proposal_from_approval(
            approved_record()
        )
    )

    assert proposal["task_id"] == (
        "scheduled_updates"
    )

    assert proposal["condition"] == (
        "HOST_UNHEALTHY"
    )

    assert proposal["reason"] == (
        "Approved evidence."
    )

    assert proposal["evidence"][
        "target_id"
    ] == "pve01"

    assert proposal["evidence"][
        "source_id"
    ] == "himp"


def test_due_execution_reuses_execution_verification_and_audit():
    execution = FakeExecution()

    repository = FakeRepository()

    approvals = FakeApprovals(
        approved_record()
    )

    verification = FakeVerification()
    audit = FakeAudit()

    service = RemediationSchedulingService(
        repository=repository,
        approvals=approvals,
        execution=execution,
        verification=verification,
        audit=audit,
    )

    now = datetime.now()

    record = repository.create(
        approval_id=7,
        scheduled_for=(
            now - timedelta(minutes=1)
        ),
        scheduled_by="admin",
    )

    result = service.execute_due(
        schedule_id=record["id"],
        now=now,
    )

    assert result["status"] == "COMPLETED"
    assert result["audit_id"] == 55

    assert execution.calls[0][
        "confirmed"
    ] is True

    assert execution.calls[0][
        "proposal"
    ]["task_id"] == "scheduled_updates"

    assert len(
        verification.calls
    ) == 1

    assert audit.calls[0][
        "confirmed"
    ] is True


def test_policy_block_fails_closed_and_is_audited():
    execution = FakeExecution(
        decision="DENY"
    )

    repository = FakeRepository()

    service = RemediationSchedulingService(
        repository=repository,
        approvals=FakeApprovals(),
        execution=execution,
        verification=FakeVerification(),
        audit=FakeAudit(),
    )

    now = datetime.now()

    record = repository.create(
        approval_id=7,
        scheduled_for=(
            now - timedelta(minutes=1)
        ),
        scheduled_by="admin",
    )

    result = service.execute_due(
        record["id"],
        now=now,
    )

    assert result["status"] == "FAILED"
    assert (
        "policy did not allow"
        in result["error"]
    )
    assert result["audit_id"] == 55


def test_failed_automation_marks_schedule_failed():
    execution = FakeExecution(
        success=False
    )

    repository = FakeRepository()

    service = RemediationSchedulingService(
        repository=repository,
        approvals=FakeApprovals(),
        execution=execution,
        verification=FakeVerification(),
        audit=FakeAudit(),
    )

    now = datetime.now()

    record = repository.create(
        approval_id=7,
        scheduled_for=(
            now - timedelta(minutes=1)
        ),
        scheduled_by="admin",
    )

    result = service.execute_due(
        record["id"],
        now=now,
    )

    assert result["status"] == "FAILED"
    assert (
        "automation execution failed"
        in result["error"]
    )


def test_second_execution_attempt_is_not_claimed():
    service, repository = make_service()

    now = datetime.now()

    record = repository.create(
        approval_id=7,
        scheduled_for=(
            now - timedelta(minutes=1)
        ),
        scheduled_by="admin",
    )

    first = service.execute_due(
        record["id"],
        now=now,
    )

    second = service.execute_due(
        record["id"],
        now=now,
    )

    assert first["status"] == "COMPLETED"
    assert second is None


def test_successful_execution_with_failed_verification_fails_schedule():
    class FailedVerification:
        def verify(
            self,
            proposal,
            remediation,
        ):
            return {
                "status": "NOT_VERIFIED",
                "success": False,
                "hostname": "pve01",
            }

    repository = FakeRepository()

    service = RemediationSchedulingService(
        repository=repository,
        approvals=FakeApprovals(),
        execution=FakeExecution(
            success=True
        ),
        verification=FailedVerification(),
        audit=FakeAudit(),
    )

    now = datetime.now()

    record = repository.create(
        approval_id=7,
        scheduled_for=(
            now - timedelta(minutes=1)
        ),
        scheduled_by="admin",
    )

    result = service.execute_due(
        record["id"],
        now=now,
    )

    assert result["status"] == "FAILED"

    assert result["audit_id"] == 55

    assert (
        "verification did not confirm recovery"
        in result["error"]
    )

    assert (
        "NOT_VERIFIED"
        in result["error"]
    )


def test_successful_execution_with_unsupported_verification_fails_schedule():
    class UnsupportedVerification:
        def verify(
            self,
            proposal,
            remediation,
        ):
            return {
                "status": "NOT_SUPPORTED",
                "success": False,
                "hostname": "pve01",
            }

    repository = FakeRepository()

    service = RemediationSchedulingService(
        repository=repository,
        approvals=FakeApprovals(),
        execution=FakeExecution(
            success=True
        ),
        verification=UnsupportedVerification(),
        audit=FakeAudit(),
    )

    now = datetime.now()

    record = repository.create(
        approval_id=7,
        scheduled_for=(
            now - timedelta(minutes=1)
        ),
        scheduled_by="admin",
    )

    result = service.execute_due(
        record["id"],
        now=now,
    )

    assert result["status"] == "FAILED"

    assert (
        "NOT_SUPPORTED"
        in result["error"]
    )
