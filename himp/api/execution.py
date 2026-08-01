"""
Execution API
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from himp.services.execution import ExecutionService

router = APIRouter()

execution = ExecutionService()


@router.post("/plugins/{plugin}/run")
def run_plugin(plugin: str):

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
def execution_history():

    return JSONResponse(
        execution.history()
    )
