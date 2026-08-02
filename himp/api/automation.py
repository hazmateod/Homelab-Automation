"""
Automation API.

Provides automation status and execution operations.
"""

from dataclasses import asdict, is_dataclass

from pydantic import BaseModel

from fastapi import APIRouter, HTTPException
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
