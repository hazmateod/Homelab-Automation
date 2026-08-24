"""
Execution API.

Provides plugin execution operations and history.
"""

import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from himp.services.execution import ExecutionService


router = APIRouter(
    tags=["Execution"],
)


execution = ExecutionService()


@router.post("/plugins/{plugin}/run")
def run_plugin(
    plugin: str,
):

    result = execution.run(plugin)

    return JSONResponse(
        {
            "plugin": result.plugin,
            "success": result.success,
            "return_code": result.return_code,
            "elapsed": result.elapsed,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "warnings": result.warnings,
            "artifacts": result.artifacts,
        }
    )


@router.get("/executions")
def execution_history(
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
    ),
):

    return JSONResponse(
        execution.history(limit)
    )


@router.get("/executions/id/{execution_id}")
def execution_detail(
    execution_id: int,
):

    result = execution.repository.find(
        execution_id
    )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Execution not found",
        )

    try:

        result["warnings"] = json.loads(
            result.get("warnings") or "[]"
        )

    except (TypeError, json.JSONDecodeError):

        result["warnings"] = []

    try:

        result["artifacts"] = json.loads(
            result.get("artifacts") or "[]"
        )

    except (TypeError, json.JSONDecodeError):

        result["artifacts"] = []

    return JSONResponse(
        jsonable_encoder(result)
    )


@router.get("/executions/{plugin}")
def plugin_execution_history(
    plugin: str,
):

    history = [
        item
        for item in execution.history(500)
        if item["plugin"] == plugin
    ]

    if not history:

        raise HTTPException(
            status_code=404,
            detail="Execution plugin not found",
        )

    return JSONResponse(
        {
            "plugin": plugin,
            "count": len(history),
            "history": history,
        }
    )


@router.get("/executions/{plugin}/latest")
def plugin_latest_execution(
    plugin: str,
):

    result = execution.latest(plugin)

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Latest execution not found",
        )

    return JSONResponse(
        result
    )
