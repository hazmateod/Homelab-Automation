"""
Remediation API.

Exposes proposal generation, remediation workflow execution,
and remediation audit history through the existing authenticated
HIMP API.
"""

from pydantic import BaseModel, Field

from fastapi import APIRouter

from himp.database.remediation_audit import (
    RemediationAuditRepository,
)
from himp.services.remediation_proposals import (
    RemediationProposalService,
)
from himp.services.remediation_workflow import (
    RemediationWorkflowService,
)


router = APIRouter(
    tags=["Remediation"],
)


remediation_proposal_service = (
    RemediationProposalService()
)

remediation_workflow_service = (
    RemediationWorkflowService(
        proposals=remediation_proposal_service,
    )
)

remediation_audit_repository = (
    RemediationAuditRepository()
)

class RemediationProposalRequest(BaseModel):
    source_type: str = Field(
        min_length=1,
    )
    source_id: str = Field(
        min_length=1,
    )
    baseline: str | None = None
    change_limit: int = Field(
        default=10,
        ge=1,
    )


class RemediationRunRequest(BaseModel):
    source_type: str = Field(
        min_length=1,
    )
    source_id: str = Field(
        min_length=1,
    )
    baseline: str | None = None
    change_limit: int = Field(
        default=10,
        ge=1,
    )
    confirmed: bool = False


@router.post(
    "/remediation/proposals",
)
def generate_remediation_proposals(
    request: RemediationProposalRequest,
):
    return remediation_proposal_service.propose(
        source_type=request.source_type,
        source_id=request.source_id,
        baseline=request.baseline,
        change_limit=request.change_limit,
    )


@router.post(
    "/remediation/run",
)
def run_remediation(
    request: RemediationRunRequest,
):
    return remediation_workflow_service.run(
        source_type=request.source_type,
        source_id=request.source_id,
        baseline=request.baseline,
        change_limit=request.change_limit,
        confirmed=request.confirmed,
    )


@router.get(
    "/remediation/audit",
)
def remediation_audit_history(
    limit: int = 50,
    source_type: str | None = None,
    source_id: str | None = None,
    decision: str | None = None,
):
    if limit < 1:
        raise ValueError(
            "limit must be greater than zero"
        )

    history = remediation_audit_repository.history(
        limit=limit,
        source_type=source_type,
        source_id=source_id,
        decision=decision,
    )

    return {
        "count": len(history),
        "history": history,
    }
