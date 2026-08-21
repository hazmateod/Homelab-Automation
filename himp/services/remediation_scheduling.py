"""
Remediation Scheduling Service.

Coordinates one-time execution of individually approved remediation
recommendations while reusing HIMP's existing remediation execution,
verification, audit, and automation infrastructure.

The scheduler process remains owned by HIMP's existing scheduler.
"""

from datetime import datetime, timezone

from himp.database.remediation_approvals import (
    RemediationApprovalRepository,
)
from himp.database.remediation_audit import (
    RemediationAuditRepository,
)
from himp.database.remediation_schedules import (
    RemediationScheduleRepository,
)
from himp.services.automation import AutomationService
from himp.services.remediation_audit import (
    RemediationAuditService,
)
from himp.services.remediation_execution import (
    RemediationExecutionService,
)
from himp.services.remediation_policy import (
    RemediationPolicyService,
)
from himp.services.remediation_verification import (
    RemediationVerificationService,
)


class RemediationSchedulingService:
    """
    Schedules and executes individually approved remediation.
    """

    def __init__(
        self,
        repository=None,
        approvals=None,
        execution=None,
        verification=None,
        audit=None,
    ):
        self.repository = (
            repository
            if repository is not None
            else RemediationScheduleRepository()
        )

        self.approvals = (
            approvals
            if approvals is not None
            else RemediationApprovalRepository()
        )

        if execution is not None:
            self.execution = execution
        else:
            automation = AutomationService()

            self.execution = RemediationExecutionService(
                policy=RemediationPolicyService(
                    automation=automation,
                ),
                automation=automation,
            )

        self.verification = (
            verification
            if verification is not None
            else RemediationVerificationService()
        )

        self.audit = (
            audit
            if audit is not None
            else RemediationAuditService(
                repository=RemediationAuditRepository()
            )
        )

    @staticmethod
    def _now():
        return datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )

    @staticmethod
    def _normalize_datetime(value):
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError as exc:
                raise ValueError(
                    "scheduled_for must use ISO datetime format"
                ) from exc

        if not isinstance(value, datetime):
            raise ValueError(
                "scheduled_for must be a datetime"
            )

        if value.tzinfo is None:
            value = value.astimezone()

        return value.astimezone(
            timezone.utc
        ).replace(
            tzinfo=None
        )

    def schedule(
        self,
        approval_id,
        scheduled_for,
        scheduled_by,
    ):
        approval = self.approvals.find(
            approval_id
        )

        if approval is None:
            raise KeyError(
                f"approval does not exist: {approval_id}"
            )

        if approval["status"] != "APPROVED":
            raise ValueError(
                "only an approved remediation can be scheduled"
            )

        if (
            not isinstance(scheduled_by, str)
            or not scheduled_by.strip()
        ):
            raise ValueError(
                "scheduled_by is required"
            )

        scheduled_for = self._normalize_datetime(
            scheduled_for
        )

        if scheduled_for <= self._now():
            raise ValueError(
                "scheduled_for must be in the future"
            )

        if self.repository.find_by_approval(
            approval_id
        ) is not None:
            raise ValueError(
                "approval already has a remediation schedule"
            )

        return self.repository.create(
            approval_id=approval_id,
            scheduled_for=scheduled_for,
            scheduled_by=scheduled_by,
        )

    def get(self, schedule_id):
        schedule = self.repository.find(
            schedule_id
        )

        if schedule is None:
            raise KeyError(
                "remediation schedule does not exist: "
                f"{schedule_id}"
            )

        return schedule

    def list(
        self,
        limit=100,
        status=None,
    ):
        schedules = self.repository.list(
            limit=limit,
            status=status,
        )

        return {
            "count": len(schedules),
            "summary": self.repository.summary(),
            "schedules": schedules,
        }

    def due(
        self,
        now=None,
        limit=100,
    ):
        if now is not None:
            now = self._normalize_datetime(
                now
            )

        return self.repository.due(
            now=now,
            limit=limit,
        )

    def cancel(
        self,
        schedule_id,
        cancelled_by,
        cancellation_note=None,
    ):
        if (
            not isinstance(cancelled_by, str)
            or not cancelled_by.strip()
        ):
            raise ValueError(
                "cancelled_by is required"
            )

        return self.repository.cancel(
            schedule_id=schedule_id,
            cancelled_by=cancelled_by,
            cancellation_note=cancellation_note,
        )

    def execute_due(
        self,
        schedule_id,
        now=None,
    ):
        if now is not None:
            now = self._normalize_datetime(
                now
            )

        claimed = self.repository.claim(
            schedule_id=schedule_id,
            now=now,
        )

        if claimed is None:
            return None

        approval = self.approvals.find(
            claimed["approval_id"]
        )

        if approval is None:
            return self.repository.fail(
                schedule_id=schedule_id,
                error="approved remediation record no longer exists",
            )

        if approval["status"] != "APPROVED":
            return self.repository.fail(
                schedule_id=schedule_id,
                error="remediation approval is no longer approved",
            )

        proposal = self._proposal_from_approval(
            approval
        )

        audit_id = None

        try:
            remediation = self.execution.execute(
                proposal,
                confirmed=True,
            )

            if remediation["decision"] == "ALLOW":
                remediation["verification"] = (
                    self.verification.verify(
                        proposal=proposal,
                        remediation=remediation,
                    )
                )

            audit_record = self.audit.record(
                source_type=approval["source_type"],
                source_id=approval["source_id"],
                proposal=proposal,
                remediation=remediation,
                confirmed=True,
            )

            if audit_record is not None:
                audit_id = audit_record.get(
                    "id"
                )

            if remediation["decision"] != "ALLOW":
                return self.repository.fail(
                    schedule_id=schedule_id,
                    audit_id=audit_id,
                    error=(
                        "remediation policy did not allow "
                        f"execution: {remediation['decision']}"
                    ),
                )

            execution = remediation.get(
                "execution"
            ) or {}

            if execution.get("success") is False:
                return self.repository.fail(
                    schedule_id=schedule_id,
                    audit_id=audit_id,
                    error="remediation automation execution failed",
                )

            return self.repository.complete(
                schedule_id=schedule_id,
                audit_id=audit_id,
            )

        except Exception as exc:
            return self.repository.fail(
                schedule_id=schedule_id,
                audit_id=audit_id,
                error=str(exc),
            )

    @staticmethod
    def _proposal_from_approval(
        approval,
    ):
        evidence = dict(
            approval.get(
                "evidence",
                {},
            )
        )

        evidence.setdefault(
            "source_type",
            approval["source_type"],
        )
        evidence.setdefault(
            "source_id",
            approval["source_id"],
        )
        evidence.setdefault(
            "target_type",
            approval["target_type"],
        )
        evidence.setdefault(
            "target_id",
            approval["target_id"],
        )

        return {
            "task_id": approval["task_id"],
            "reason": approval["rationale"],
            "evidence": evidence,
        }
