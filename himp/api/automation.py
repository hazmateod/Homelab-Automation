"""
Automation API.

Provides automation status and execution operations.
"""

from dataclasses import asdict, is_dataclass

from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from himp.app import HIMP


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


@router.post("/automation/{task_id}/run")
def run_automation(
    task_id: str,
):

    try:

        result = himp.automation.run(
            task_id
        )

        return JSONResponse(
            serialize(result)
        )


    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error),
        )


    except RuntimeError as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )
