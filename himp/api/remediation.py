"""
Remediation API.

Exposes recommendation intelligence, proposal generation, remediation
workflow execution, and remediation audit history through the existing
authenticated HIMP API.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from himp.api.dependencies import require_admin

from himp.database.remediation_audit import (
    RemediationAuditRepository,
)
from himp.services.automation import (
    AutomationService,
)
from himp.services.remediation_approvals import (
    RemediationApprovalService,
)
from himp.services.remediation_proposals import (
    RemediationProposalService,
)
from himp.services.remediation_autonomy import (
    RemediationAutonomyPolicyService,
)
from himp.services.remediation_recommendations import (
    RemediationRecommendationService,
)
from himp.services.remediation_scheduling import (
    RemediationSchedulingService,
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

remediation_autonomy_service = (
    RemediationAutonomyPolicyService(
        automation=AutomationService(),
    )
)

remediation_recommendation_service = (
    RemediationRecommendationService(
        autonomy=remediation_autonomy_service,
    )
)

remediation_approval_service = (
    RemediationApprovalService(
        recommendations=remediation_recommendation_service,
    )
)


remediation_scheduling_service = (
    RemediationSchedulingService()
)


remediation_workflow_service = (
    RemediationWorkflowService(
        proposals=remediation_proposal_service,
    )
)

remediation_audit_repository = (
    RemediationAuditRepository()
)




class RemediationApprovalCreateRequest(BaseModel):
    entity_type: str = Field(
        min_length=1,
    )
    entity_id: str = Field(
        min_length=1,
    )
    recommendation_id: str = Field(
        min_length=1,
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=500,
    )


class RemediationApprovalDecisionRequest(BaseModel):
    note: str | None = Field(
        default=None,
        max_length=2000,
    )


class RemediationScheduleCreateRequest(BaseModel):
    scheduled_for: datetime


class RemediationScheduleCancelRequest(BaseModel):
    note: str | None = Field(
        default=None,
        max_length=2000,
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


@router.get(
    "/remediation/recommendations/{entity_type}/{entity_id}",
)
def remediation_recommendations(
    entity_type: str,
    entity_id: str,
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
):
    """
    Return read-only, evidence-backed operator recommendations.

    This endpoint never executes remediation.
    """

    return remediation_recommendation_service.recommend(
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )




@router.post(
    "/remediation/approvals",
)
def create_remediation_approval(
    request: RemediationApprovalCreateRequest,
    admin=Depends(require_admin),
):
    try:
        return remediation_approval_service.enqueue(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            recommendation_id=request.recommendation_id,
            requested_by=admin.username,
            limit=request.limit,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@router.get(
    "/remediation/approvals",
)
def remediation_approval_queue(
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    status: str | None = Query(
        default=None,
    ),
):
    try:
        return remediation_approval_service.list(
            limit=limit,
            status=status,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@router.get(
    "/remediation/approvals/{approval_id}",
)
def remediation_approval_detail(
    approval_id: int,
):
    try:
        return remediation_approval_service.get(
            approval_id
        )
    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error


@router.post(
    "/remediation/approvals/{approval_id}/approve",
)
def approve_remediation(
    approval_id: int,
    request: RemediationApprovalDecisionRequest,
    admin=Depends(require_admin),
):
    try:
        return remediation_approval_service.approve(
            approval_id=approval_id,
            decided_by=admin.username,
            decision_note=request.note,
        )
    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error


@router.post(
    "/remediation/approvals/{approval_id}/deny",
)
def deny_remediation(
    approval_id: int,
    request: RemediationApprovalDecisionRequest,
    admin=Depends(require_admin),
):
    try:
        return remediation_approval_service.deny(
            approval_id=approval_id,
            decided_by=admin.username,
            decision_note=request.note,
        )
    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error



@router.post(
    "/remediation/schedules",
)
def create_remediation_schedule(
    approval_id: int,
    request: RemediationScheduleCreateRequest,
    admin=Depends(require_admin),
):
    try:
        return remediation_scheduling_service.schedule(
            approval_id=approval_id,
            scheduled_for=request.scheduled_for,
            scheduled_by=admin.username,
        )
    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error


@router.get(
    "/remediation/schedules",
)
def remediation_schedule_queue(
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    status: str | None = Query(
        default=None,
    ),
):
    try:
        return remediation_scheduling_service.list(
            limit=limit,
            status=status,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@router.get(
    "/remediation/schedules/{schedule_id}",
)
def remediation_schedule_detail(
    schedule_id: int,
):
    try:
        return remediation_scheduling_service.get(
            schedule_id
        )
    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error


@router.post(
    "/remediation/schedules/{schedule_id}/cancel",
)
def cancel_remediation_schedule(
    schedule_id: int,
    request: RemediationScheduleCancelRequest,
    admin=Depends(require_admin),
):
    try:
        return remediation_scheduling_service.cancel(
            schedule_id=schedule_id,
            cancelled_by=admin.username,
            cancellation_note=request.note,
        )
    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error


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
