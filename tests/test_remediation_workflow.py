import pytest

from himp.services.remediation_workflow import (
    RemediationWorkflowService,
)


class FakeProposalService:
    def __init__(
        self,
        proposals=None,
    ):
        self.proposals = proposals or []
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

        return {
            "source_type": source_type,
            "source_id": source_id,
            "proposals": self.proposals,
        }


class FakeExecutionService:
    def __init__(
        self,
        decisions=None,
    ):
        self.decisions = decisions or []
        self.calls = []

    def execute(
        self,
        proposal,
        confirmed=False,
    ):
        self.calls.append(
            (
                proposal,
                confirmed,
            )
        )

        decision = (
            self.decisions.pop(0)
            if self.decisions
            else "ALLOW"
        )

        result = {
            "decision": decision,
            "policy": {
                "decision": decision,
                "task_id": proposal["task_id"],
                "reason": proposal["reason"],
                "evidence": proposal["evidence"],
                "risk_level": "maintenance",
                "confirmation_required": (
                    decision == "CONFIRM_REQUIRED"
                ),
            },
        }

        if decision == "ALLOW":
            result["execution"] = {
                "id": 42,
                "success": True,
            }

        return result


def proposal(
    task_id="scheduled_updates",
):
    return {
        "task_id": task_id,
        "reason": (
            "Host health indicates maintenance is required."
        ),
        "evidence": {
            "hostname": "pve01",
            "status": "WARNING",
        },
    }


def make_service(
    proposals=None,
    decisions=None,
):
    proposal_service = FakeProposalService(
        proposals=proposals,
    )

    execution_service = FakeExecutionService(
        decisions=decisions,
    )

    service = RemediationWorkflowService(
        proposals=proposal_service,
        execution=execution_service,
    )

    return (
        service,
        proposal_service,
        execution_service,
    )


def test_remediation_workflow_executes_proposals():
    service, proposal_service, execution_service = (
        make_service(
            proposals=[
                proposal(),
            ],
            decisions=[
                "ALLOW",
            ],
        )
    )

    result = service.run(
        source_type="host",
        source_id="pve01",
    )

    assert result["source_type"] == "host"
    assert result["source_id"] == "pve01"

    assert result["proposal_count"] == 1
    assert result["executed_count"] == 1
    assert result["blocked_count"] == 0

    assert result["results"][0]["decision"] == "ALLOW"
    assert result["results"][0]["execution"]["success"] is True

    assert proposal_service.calls == [
        {
            "source_type": "host",
            "source_id": "pve01",
            "baseline": None,
            "change_limit": 10,
        }
    ]

    assert len(execution_service.calls) == 1
    assert execution_service.calls[0][1] is False


def test_remediation_workflow_preserves_denied_proposals():
    service, _, execution_service = make_service(
        proposals=[
            proposal(),
        ],
        decisions=[
            "DENY",
        ],
    )

    result = service.run(
        source_type="host",
        source_id="pve01",
    )

    assert result["proposal_count"] == 1
    assert result["executed_count"] == 0
    assert result["blocked_count"] == 1

    assert result["results"][0]["decision"] == "DENY"
    assert "execution" not in result["results"][0]

    assert len(execution_service.calls) == 1


def test_remediation_workflow_preserves_confirmation_required():
    service, _, execution_service = make_service(
        proposals=[
            proposal(),
        ],
        decisions=[
            "CONFIRM_REQUIRED",
        ],
    )

    result = service.run(
        source_type="host",
        source_id="pve01",
    )

    assert result["proposal_count"] == 1
    assert result["executed_count"] == 0
    assert result["blocked_count"] == 1

    assert result["results"][0]["decision"] == (
        "CONFIRM_REQUIRED"
    )
    assert (
        result["results"][0]["policy"][
            "confirmation_required"
        ]
        is True
    )


def test_remediation_workflow_passes_confirmation():
    service, _, execution_service = make_service(
        proposals=[
            proposal(),
        ],
        decisions=[
            "ALLOW",
        ],
    )

    result = service.run(
        source_type="host",
        source_id="pve01",
        confirmed=True,
    )

    assert result["results"][0]["decision"] == "ALLOW"

    assert execution_service.calls == [
        (
            proposal(),
            True,
        )
    ]


def test_remediation_workflow_supports_multiple_proposals():
    proposals = [
        proposal(
            task_id="scheduled_updates",
        ),
        {
            "task_id": "restart_service",
            "reason": "Related service requires restart.",
            "evidence": {
                "hostname": "pve01",
                "service": "example",
            },
        },
    ]

    service, _, execution_service = make_service(
        proposals=proposals,
        decisions=[
            "ALLOW",
            "DENY",
        ],
    )

    result = service.run(
        source_type="host",
        source_id="pve01",
    )

    assert result["proposal_count"] == 2
    assert result["executed_count"] == 1
    assert result["blocked_count"] == 1

    assert [
        item["decision"]
        for item in result["results"]
    ] == [
        "ALLOW",
        "DENY",
    ]

    assert len(execution_service.calls) == 2


def test_remediation_workflow_returns_empty_result_when_no_proposals():
    service, _, execution_service = make_service()

    result = service.run(
        source_type="host",
        source_id="pve01",
    )

    assert result == {
        "source_type": "host",
        "source_id": "pve01",
        "baseline": None,
        "proposal_count": 0,
        "executed_count": 0,
        "blocked_count": 0,
        "verification_count": 0,
        "audit_ids": [],
        "results": [],
    }

    assert execution_service.calls == []


def test_remediation_workflow_proposal_errors_propagate():
    class FailingProposalService:
        def propose(
            self,
            source_type,
            source_id,
            baseline=None,
            change_limit=10,
        ):
            raise RuntimeError(
                "proposal generation failed"
            )

    service = RemediationWorkflowService(
        proposals=FailingProposalService(),
        execution=FakeExecutionService(),
    )

    with pytest.raises(
        RuntimeError,
        match="proposal generation failed",
    ):
        service.run(
            source_type="host",
            source_id="pve01",
        )


def test_remediation_workflow_execution_errors_propagate():
    class FailingExecutionService:
        def execute(
            self,
            proposal,
            confirmed=False,
        ):
            raise RuntimeError(
                "remediation execution failed"
            )

    service = RemediationWorkflowService(
        proposals=FakeProposalService(
            proposals=[
                proposal(),
            ]
        ),
        execution=FailingExecutionService(),
    )

    with pytest.raises(
        RuntimeError,
        match="remediation execution failed",
    ):
        service.run(
            source_type="host",
            source_id="pve01",
        )


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
            "id": len(self.calls),
        }


def make_audited_workflow(
    proposals=None,
    execution=None,
):
    proposal_service = FakeProposalService(
        proposals=proposals
        or []
    )

    execution_service = (
        execution
        or FakeExecutionService()
    )

    audit_service = FakeAudit()

    workflow = RemediationWorkflowService(
        proposals=proposal_service,
        execution=execution_service,
        audit=audit_service,
    )

    return (
        workflow,
        proposal_service,
        execution_service,
        audit_service,
    )


def test_allowed_remediation_is_audited():
    proposal = {
        "task_id": "scheduled_updates",
        "reason": "Maintenance required.",
        "evidence": {
            "hostname": "pve01",
        },
    }

    (
        workflow,
        _,
        _,
        audit,
    ) = make_audited_workflow(
        proposals=[proposal]
    )

    result = workflow.run(
        source_type="host",
        source_id="pve01",
    )

    assert result["executed_count"] == 1
    assert len(audit.calls) == 1
    assert audit.calls[0]["source_type"] == "host"
    assert audit.calls[0]["source_id"] == "pve01"
    assert audit.calls[0]["proposal"] == proposal
    assert audit.calls[0]["remediation"]["decision"] == "ALLOW"
    assert audit.calls[0]["confirmed"] is False


def test_blocked_remediation_is_audited():
    proposal = {
        "task_id": "scheduled_updates",
        "reason": "Maintenance required.",
        "evidence": {
            "hostname": "pve01",
        },
    }

    (
        workflow,
        _,
        execution,
        audit,
    ) = make_audited_workflow(
        proposals=[proposal],
        execution=FakeExecutionService(
            decisions=["DENY"]
        ),
    )

    result = workflow.run(
        source_type="host",
        source_id="pve01",
    )

    assert result["blocked_count"] == 1
    assert execution.calls == [
        (
            proposal,
            False,
        )
    ]
    assert len(audit.calls) == 1
    assert audit.calls[0]["remediation"]["decision"] == "DENY"


def test_confirmation_required_remediation_is_audited():
    proposal = {
        "task_id": "scheduled_updates",
        "reason": "Maintenance required.",
        "evidence": {
            "hostname": "pve01",
        },
    }

    (
        workflow,
        _,
        _,
        audit,
    ) = make_audited_workflow(
        proposals=[proposal],
        execution=FakeExecutionService(
            decisions=["CONFIRM_REQUIRED"]
        ),
    )

    result = workflow.run(
        source_type="host",
        source_id="pve01",
    )

    assert result["blocked_count"] == 1
    assert len(audit.calls) == 1
    assert (
        audit.calls[0]["remediation"]["decision"]
        == "CONFIRM_REQUIRED"
    )


def test_confirmation_state_is_passed_to_audit():
    proposal = {
        "task_id": "scheduled_updates",
        "reason": "Maintenance required.",
        "evidence": {
            "hostname": "pve01",
        },
    }

    (
        workflow,
        _,
        execution,
        audit,
    ) = make_audited_workflow(
        proposals=[proposal]
    )

    workflow.run(
        source_type="host",
        source_id="pve01",
        confirmed=True,
    )

    assert execution.calls == [
        (
            proposal,
            True,
        )
    ]

    assert audit.calls[0]["confirmed"] is True


def test_multiple_remediations_create_multiple_audit_records():
    proposals = [
        {
            "task_id": "scheduled_updates",
            "reason": "First remediation.",
            "evidence": {
                "hostname": "pve01",
            },
        },
        {
            "task_id": "scheduled_updates",
            "reason": "Second remediation.",
            "evidence": {
                "hostname": "pve02",
            },
        },
    ]

    (
        workflow,
        _,
        _,
        audit,
    ) = make_audited_workflow(
        proposals=proposals
    )

    result = workflow.run(
        source_type="host",
        source_id="cluster",
    )

    assert result["proposal_count"] == 2
    assert result["executed_count"] == 2
    assert len(audit.calls) == 2

    assert [
        call["proposal"]["evidence"]["hostname"]
        for call in audit.calls
    ] == [
        "pve01",
        "pve02",
    ]


def test_audit_failure_propagates():
    class FailingAudit(FakeAudit):
        def record(
            self,
            source_type,
            source_id,
            proposal,
            remediation,
            confirmed=False,
        ):
            raise RuntimeError(
                "audit persistence failed"
            )

    proposal = {
        "task_id": "scheduled_updates",
        "reason": "Maintenance required.",
        "evidence": {
            "hostname": "pve01",
        },
    }

    proposal_service = FakeProposalService(
        proposals=[proposal]
    )

    workflow = RemediationWorkflowService(
        proposals=proposal_service,
        execution=FakeExecutionService(),
        audit=FailingAudit(),
    )

    with pytest.raises(
        RuntimeError,
        match="audit persistence failed",
    ):
        workflow.run(
            source_type="host",
            source_id="pve01",
        )


class FakeVerificationService:
    def __init__(
        self,
        result=None,
    ):
        self.result = result or {
            "status": "VERIFIED",
            "success": True,
            "hostname": "pve02",
        }
        self.calls = []

    def verify(
        self,
        proposal,
        remediation,
    ):
        self.calls.append(
            {
                "proposal": proposal,
                "remediation": remediation,
            }
        )

        return self.result


def make_verified_workflow(
    proposals=None,
    execution=None,
    audit=None,
    verification=None,
):
    proposal_service = (
        FakeProposalService(
            proposals=proposals or [
                {
                    "task_id": "scheduled_updates",
                    "reason": "Maintenance required.",
                    "evidence": {
                        "target_type": "host",
                        "target_id": "pve02",
                    },
                }
            ]
        )
    )

    execution_service = (
        execution
        or FakeExecutionService()
    )

    audit_service = (
        audit
        or FakeAudit()
    )

    verification_service = (
        verification
        or FakeVerificationService()
    )

    workflow = RemediationWorkflowService(
        proposals=proposal_service,
        execution=execution_service,
        audit=audit_service,
        verification=verification_service,
    )

    return (
        workflow,
        proposal_service,
        execution_service,
        verification_service,
        audit_service,
    )


def test_allowed_remediation_is_verified():
    (
        workflow,
        _,
        execution,
        verification,
        audit,
    ) = make_verified_workflow()

    result = workflow.run(
        source_type="host",
        source_id="pve01",
    )

    assert result["verification_count"] == 1
    assert result["results"][0]["verification"] == {
        "status": "VERIFIED",
        "success": True,
        "hostname": "pve02",
    }

    assert len(execution.calls) == 1
    assert len(verification.calls) == 1
    assert len(audit.calls) == 1


def test_denied_remediation_is_not_verified():
    proposal = {
        "task_id": "scheduled_updates",
        "reason": "Maintenance required.",
        "evidence": {
            "target_type": "host",
            "target_id": "pve02",
        },
    }

    execution = FakeExecutionService(
        decisions=["DENY"]
    )

    (
        workflow,
        _,
        _,
        verification,
        audit,
    ) = make_verified_workflow(
        proposals=[proposal],
        execution=execution,
    )

    result = workflow.run(
        source_type="host",
        source_id="pve01",
    )

    assert result["blocked_count"] == 1
    assert result["verification_count"] == 0
    assert verification.calls == []
    assert len(audit.calls) == 1


def test_failed_verification_is_returned():
    verification = FakeVerificationService(
        result={
            "status": "FAILED",
            "success": False,
            "hostname": "pve02",
        }
    )

    (
        workflow,
        _,
        _,
        _,
        _,
    ) = make_verified_workflow(
        verification=verification,
    )

    result = workflow.run(
        source_type="host",
        source_id="pve01",
    )

    assert result["verification_count"] == 1
    assert result["results"][0]["verification"] == {
        "status": "FAILED",
        "success": False,
        "hostname": "pve02",
    }
