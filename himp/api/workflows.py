"""
Workflow definition API.

Provides CRUD and validation operations for workflow definitions.
"""

from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from himp.services.workflow_execution import (
    WorkflowExecutionService,
)
from himp.services.workflow_history import (
    WorkflowHistoryService,
)
from himp.services.workflow_retry_replay import (
    WorkflowRetryReplayError,
    WorkflowRetryReplayService,
)
from himp.services.automation import (
    AutomationAlreadyRunningError,
    AutomationConfirmationRequiredError,
    AutomationDependencyNotSatisfiedError,
    AutomationDisabledError,
)
from himp.api.dependencies import require_admin
from himp.services.workflows import (
    WorkflowDependencyCycleError,
    WorkflowDependencyNotFoundError,
    WorkflowNotFoundError,
    WorkflowService,
    WorkflowTaskNotFoundError,
    WorkflowValidationError,
)


router = APIRouter(
    tags=["Workflows"],
)


workflow_service = WorkflowService()

workflow_execution_service = WorkflowExecutionService(
    workflow_service=workflow_service,
)

workflow_history_service = WorkflowHistoryService(
    workflow_service=workflow_service,
)

workflow_retry_replay_service = WorkflowRetryReplayService(
    workflow_service=workflow_service,
    workflow_execution_service=workflow_execution_service,
)


class WorkflowCreateRequest(BaseModel):
    name: str
    description: str = ""
    enabled: bool = True


class WorkflowUpdateRequest(BaseModel):
    name: str
    description: str = ""
    enabled: bool = True


class WorkflowTaskRequest(BaseModel):
    task_id: str
    position: int = 0


class WorkflowDependencyRequest(BaseModel):
    task_id: str
    depends_on_task_id: str


class WorkflowExecuteRequest(BaseModel):
    limit: int | None = None
    confirmed: bool = False


class WorkflowRetryRequest(BaseModel):
    confirmed: bool = False


class WorkflowReplayRequest(BaseModel):
    limit: int | None = None
    confirmed: bool = False


def _not_found(error):
    raise HTTPException(
        status_code=404,
        detail=str(error),
    )


def _invalid(error):
    raise HTTPException(
        status_code=400,
        detail=str(error),
    )


@router.get("/workflows")
def list_workflows():
    return JSONResponse(
        workflow_service.list_workflows()
    )


@router.post("/workflows")
def create_workflow(
    request: WorkflowCreateRequest,
):
    try:
        workflow = workflow_service.create_workflow(
            name=request.name,
            description=request.description,
            enabled=request.enabled,
        )

        return JSONResponse(
            workflow,
            status_code=201,
        )

    except WorkflowValidationError as error:
        _invalid(error)


@router.get("/workflows/{workflow_id}")
def get_workflow(
    workflow_id: int,
):
    try:
        return JSONResponse(
            workflow_service.get_workflow(
                workflow_id
            )
        )

    except WorkflowNotFoundError as error:
        _not_found(error)


@router.put("/workflows/{workflow_id}")
def update_workflow(
    workflow_id: int,
    request: WorkflowUpdateRequest,
):
    try:
        workflow = workflow_service.update_workflow(
            workflow_id,
            name=request.name,
            description=request.description,
            enabled=request.enabled,
        )

        return JSONResponse(
            workflow
        )

    except WorkflowNotFoundError as error:
        _not_found(error)

    except WorkflowValidationError as error:
        _invalid(error)


@router.delete("/workflows/{workflow_id}")
def delete_workflow(
    workflow_id: int,
):
    try:
        workflow_service.delete_workflow(
            workflow_id
        )

        return {
            "message": "Workflow deleted successfully.",
        }

    except WorkflowNotFoundError as error:
        _not_found(error)


@router.post("/workflows/{workflow_id}/tasks")
def add_workflow_task(
    workflow_id: int,
    request: WorkflowTaskRequest,
):
    try:
        task = workflow_service.add_task(
            workflow_id,
            request.task_id,
            request.position,
        )

        return JSONResponse(
            {
                "task": task,
                "message": "Workflow task added successfully.",
            },
            status_code=201,
        )

    except WorkflowNotFoundError as error:
        _not_found(error)

    except WorkflowTaskNotFoundError as error:
        _not_found(error)

    except WorkflowValidationError as error:
        _invalid(error)

    except ValueError as error:
        _invalid(error)


@router.delete(
    "/workflows/{workflow_id}/tasks/{task_id}"
)
def remove_workflow_task(
    workflow_id: int,
    task_id: str,
):
    try:
        task = workflow_service.remove_task(
            workflow_id,
            task_id,
        )

        return JSONResponse(
            {
                "task": task,
                "message": "Workflow task removed successfully.",
            }
        )

    except WorkflowNotFoundError as error:
        _not_found(error)

    except WorkflowTaskNotFoundError as error:
        _not_found(error)


@router.post(
    "/workflows/{workflow_id}/dependencies"
)
def add_workflow_dependency(
    workflow_id: int,
    request: WorkflowDependencyRequest,
):
    try:
        dependency = workflow_service.add_dependency(
            workflow_id,
            request.task_id,
            request.depends_on_task_id,
        )

        return JSONResponse(
            {
                "dependency": dependency,
                "message": "Workflow dependency added successfully.",
            },
            status_code=201,
        )

    except WorkflowNotFoundError as error:
        _not_found(error)

    except WorkflowTaskNotFoundError as error:
        _not_found(error)

    except WorkflowDependencyCycleError as error:
        _invalid(error)

    except WorkflowValidationError as error:
        _invalid(error)


@router.delete(
    "/workflows/{workflow_id}/dependencies/"
    "{task_id}/{dependency_task_id}"
)
def remove_workflow_dependency(
    workflow_id: int,
    task_id: str,
    dependency_task_id: str,
):
    try:
        dependency = workflow_service.remove_dependency(
            workflow_id,
            task_id,
            dependency_task_id,
        )

        return JSONResponse(
            {
                "dependency": dependency,
                "message": (
                    "Workflow dependency removed successfully."
                ),
            }
        )

    except WorkflowNotFoundError as error:
        _not_found(error)

    except WorkflowDependencyNotFoundError as error:
        _not_found(error)


@router.get(
    "/workflows/{workflow_id}/validate"
)
def validate_workflow(
    workflow_id: int,
):
    try:
        return JSONResponse(
            workflow_service.validate_workflow(
                workflow_id
            )
        )

    except WorkflowNotFoundError as error:
        _not_found(error)

@router.get(
    "/workflows/{workflow_id}/history"
)
def workflow_history(
    workflow_id: int,
    limit: int = 50,
):
    try:
        return JSONResponse(
            workflow_history_service.history(
                workflow_id,
                limit=limit,
            )
        )

    except WorkflowNotFoundError as error:
        _not_found(error)


@router.get(
    "/workflows/{workflow_id}/history/"
    "{workflow_execution_id}"
)
def workflow_history_run(
    workflow_id: int,
    workflow_execution_id: str,
):
    try:
        history = workflow_history_service.get(
            workflow_id,
            workflow_execution_id,
        )

        if history is None:
            raise HTTPException(
                status_code=404,
                detail="Workflow execution does not exist.",
            )

        return JSONResponse(
            history
        )

    except WorkflowNotFoundError as error:
        _not_found(error)


@router.post(
    "/workflows/{workflow_id}/execute"
)
def execute_workflow(
    workflow_id: int,
    request: WorkflowExecuteRequest | None = None,
):
    confirmed = (
        request.confirmed
        if request is not None
        else False
    )

    try:
        return JSONResponse(
            workflow_execution_service.execute(
                workflow_id,
                limit=(
                    request.limit
                    if request is not None
                    else None
                ),
                confirmed=confirmed,
            )
        )

    except WorkflowNotFoundError as error:
        _not_found(error)

    except ValueError as error:
        _invalid(error)



@router.get(
    "/workflows/{workflow_id}/history/"
    "{workflow_execution_id}/actions"
)
def workflow_execution_actions(
    workflow_id: int,
    workflow_execution_id: str,
):
    try:
        return JSONResponse(
            workflow_retry_replay_service.capabilities(
                workflow_id,
                workflow_execution_id,
            )
        )

    except WorkflowRetryReplayError as error:
        _invalid(error)


@router.post(
    "/workflows/{workflow_id}/history/"
    "{workflow_execution_id}/retry/{execution_id}",
    dependencies=[Depends(require_admin)],
)
def retry_workflow_failed_step(
    workflow_id: int,
    workflow_execution_id: str,
    execution_id: int,
    request: WorkflowRetryRequest | None = None,
):
    confirmed = (
        request.confirmed
        if request is not None
        else False
    )

    try:
        return JSONResponse(
            jsonable_encoder(
                workflow_retry_replay_service.retry_failed_step(
                workflow_id,
                workflow_execution_id,
                execution_id,
                    confirmed=confirmed,
                )
            )
        )

    except WorkflowRetryReplayError as error:
        _invalid(error)

    except (
        AutomationAlreadyRunningError,
        AutomationDisabledError,
        AutomationConfirmationRequiredError,
        AutomationDependencyNotSatisfiedError,
    ) as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        )


@router.post(
    "/workflows/{workflow_id}/history/"
    "{workflow_execution_id}/replay",
    dependencies=[Depends(require_admin)],
)
def replay_workflow_execution(
    workflow_id: int,
    workflow_execution_id: str,
    request: WorkflowReplayRequest | None = None,
):
    confirmed = (
        request.confirmed
        if request is not None
        else False
    )

    limit = (
        request.limit
        if request is not None
        else None
    )

    try:
        return JSONResponse(
            jsonable_encoder(
                workflow_retry_replay_service.replay_workflow(
                workflow_id,
                workflow_execution_id,
                limit=limit,
                    confirmed=confirmed,
                )
            )
        )

    except WorkflowRetryReplayError as error:
        _invalid(error)

    except (
        AutomationAlreadyRunningError,
        AutomationDisabledError,
        AutomationConfirmationRequiredError,
        AutomationDependencyNotSatisfiedError,
    ) as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        )
