"""
Automation API.

Provides automation status and execution operations.
"""

from dataclasses import asdict, is_dataclass

from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from himp.app import HIMP
from himp.database.automation_progress import AutomationProgressRepository
from himp.services.automation import (
    AutomationAlreadyRunningError,
    AutomationConfirmationRequiredError,
    AutomationDependencyCycleError,
    AutomationDependencyNotFoundError,
    AutomationDependencyNotSatisfiedError,
    AutomationDisabledError,
)


router = APIRouter(
    tags=["Automation"],
)


himp = HIMP()


def serialize(value):

    if isinstance(value, BaseModel):

        return value.model_dump(
            mode="json"
        )


    if is_dataclass(value):

        return asdict(value)


    if isinstance(value, list):

        return [
            serialize(item)
            for item in value
        ]


    if isinstance(value, dict):

        return {
            key: serialize(item)
            for key, item in value.items()
        }


    return value



@router.get("/automation")
def automation_summary():

    return JSONResponse(
        himp.automation.summary()
    )



@router.get("/automation/{task_id}/status")
def automation_execution_status(
    task_id: str,
):
    try:
        return JSONResponse(
            himp.automation.active_execution_status(
                task_id
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )



def _serialize_automation_progress(record):
    """Return an explicit public allowlist of progress fields."""
    if record is None:
        return None

    return {
        "run_id": record["run_id"],
        "task_id": record["task_id"],
        "attempt": record["attempt"],
        "status": record["status"],
        "revision": record["revision"],
        "started_at": record["started_at"],
        "updated_at": record["updated_at"],
        "finished_at": record["finished_at"],
        "host_results": {
            str(hostname): {
                key: host_data[key]
                for key in (
                    "host",
                    "status",
                    "last_task",
                    "last_event",
                    "updated_at",
                    "ok",
                    "changed",
                    "failed",
                    "unreachable",
                    "skipped",
                )
                if key in host_data
            }
            for hostname, host_data in record["host_results"].items()
            if isinstance(host_data, dict)
        },
        "completed_execution_id": record["completed_execution_id"],
    }


@router.get("/automation/{task_id}/progress")
def automation_active_progress(task_id: str):
    """Return active progress for a maintenance task."""
    if task_id not in {
        "scheduled_updates",
        "update_host",
        "update_group",
    }:
        raise HTTPException(
            status_code=404,
            detail="Maintenance task not found",
        )

    repository = AutomationProgressRepository()
    record = repository.latest_running(task_id)

    return JSONResponse({
        "task_id": task_id,
        "active": record is not None,
        "progress": _serialize_automation_progress(record),
    })


@router.get("/automation/progress/{run_id}")
def automation_progress_detail(run_id: str):
    """Return progress for a specific maintenance attempt."""
    repository = AutomationProgressRepository()
    record = repository.get(run_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Automation progress run not found",
        )

    return JSONResponse(
        _serialize_automation_progress(record)
    )


@router.get("/automation/executions")
def automation_execution_history(
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
    ),
    task_id: str | None = Query(
        default=None,
    ),
    success: bool | None = Query(
        default=None,
    ),
):
    return JSONResponse(
        himp.automation.execution_repository.history(
            limit=limit,
            task_id=task_id,
            success=success,
        )
    )


@router.get("/automation/executions/id/{execution_id}")
def automation_execution_detail(
    execution_id: int,
):
    result = (
        himp.automation.execution_repository.find(
            execution_id
        )
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Automation execution not found",
        )

    return JSONResponse(result)


@router.get("/automation/executions/{task_id}")
def automation_task_execution_history(
    task_id: str,
):
    history = (
        himp.automation.execution_repository.task_history(
            task_id,
            limit=50,
        )
    )

    if not history:
        raise HTTPException(
            status_code=404,
            detail="Automation task execution history not found",
        )

    return JSONResponse(
        {
            "task_id": task_id,
            "count": len(history),
            "history": history,
        }
    )


class AutomationDependencyRequest(BaseModel):
    depends_on_task_id: str


@router.post("/automation/{task_id}/dependencies")
def add_automation_dependency(
    task_id: str,
    request: AutomationDependencyRequest,
):
    try:
        dependency = (
            himp.automation.add_dependency(
                task_id,
                request.depends_on_task_id,
            )
        )

        return JSONResponse(
            {
                "dependency": dependency,
                "message": (
                    "Automation dependency added successfully."
                ),
            }
        )

    except AutomationDependencyCycleError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.get("/automation/{task_id}/dependencies")
def automation_dependency_status(
    task_id: str,
):
    try:
        return JSONResponse(
            himp.automation.dependency_status(
                task_id
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )


@router.get("/automation/dependencies/graph")
def automation_dependency_graph():
    return JSONResponse(
        himp.automation.dependency_graph()
    )


@router.delete(
    "/automation/{task_id}/dependencies/{dependency_task_id}"
)
def remove_automation_dependency(
    task_id: str,
    dependency_task_id: str,
):
    try:
        dependency = (
            himp.automation.remove_dependency(
                task_id,
                dependency_task_id,
            )
        )

        return JSONResponse(
            {
                "dependency": dependency,
                "message": (
                    "Automation dependency removed successfully."
                ),
            }
        )

    except AutomationDependencyNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )


@router.post("/automation/{task_id}/enable")
def enable_automation(
    task_id: str,
):
    try:
        task = himp.automation.enable(
            task_id
        )

        return {
            "task": task,
            "message": "Automation task enabled successfully.",
        }

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )


@router.post("/automation/{task_id}/disable")
def disable_automation(
    task_id: str,
):
    try:
        task = himp.automation.disable(
            task_id
        )

        return {
            "task": task,
            "message": "Automation task disabled successfully.",
        }

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )


class AutomationRunRequest(BaseModel):
    confirmed: bool = False


@router.post("/automation/{task_id}/run")
def run_automation(
    task_id: str,
    request: AutomationRunRequest | None = None,
):

    confirmed = (
        request.confirmed
        if request is not None
        else False
    )

    try:

        result = himp.automation.run(
            task_id,
            confirmed=confirmed,
        )

        return JSONResponse(
            serialize(result)
        )


    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error),
        )


    except AutomationAlreadyRunningError as error:

        raise HTTPException(
            status_code=409,
            detail=str(error),
        )


    except AutomationDisabledError as error:

        raise HTTPException(
            status_code=409,
            detail=str(error),
        )


    except AutomationConfirmationRequiredError as error:

        raise HTTPException(
            status_code=409,
            detail=str(error),
        )


    except AutomationDependencyNotSatisfiedError as error:

        raise HTTPException(
            status_code=409,
            detail=str(error),
        )
