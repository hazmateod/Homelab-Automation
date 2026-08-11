"""
Scheduler API.

Provides automation schedule configuration operations.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from himp.services.scheduler import SchedulerService


class SchedulerUpdate(BaseModel):
    enabled: bool
    frequency: str
    schedule_time: str | None = None
    day_of_week: int | None = None
    day_of_month: int | None = None


router = APIRouter(
    prefix="/scheduler",
    tags=["Scheduler"],
)


service = SchedulerService()


@router.get("")
@router.get("/")
async def scheduler_summary():
    return {
        "count": len(service.all()),
        "schedules": [
            dict(schedule)
            for schedule in service.all()
        ],
    }


@router.get("/{task_id}/status")
async def scheduler_task_status(
    task_id: str,
):
    try:
        return service.execution_status(
            task_id
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": str(exc),
                "task_id": task_id,
            },
        ) from exc


@router.get("/{task_id}")
async def scheduler_task(
    task_id: str,
):
    try:
        schedule = service.find(
            task_id
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": str(exc),
                "task_id": task_id,
            },
        ) from exc

    next_run = service.next_run(schedule)

    result = dict(schedule)
    result["next_run"] = (
        next_run.isoformat()
        if next_run is not None
        else None
    )

    return result


@router.put("/{task_id}")
async def update_scheduler_task(
    task_id: str,
    request: SchedulerUpdate,
):
    try:
        schedule = service.update(
            task_id=task_id,
            enabled=request.enabled,
            frequency=request.frequency,
            schedule_time=request.schedule_time,
            day_of_week=request.day_of_week,
            day_of_month=request.day_of_month,
        )

    except ValueError as exc:
        message = str(exc)

        if message.startswith(
            "Automation task does not exist:"
        ):
            status_code = 404
        else:
            status_code = 400

        raise HTTPException(
            status_code=status_code,
            detail={
                "error": message,
                "task_id": task_id,
            },
        ) from exc

    return {
        "schedule": dict(schedule),
        "message": "Automation schedule updated successfully.",
    }


@router.post("/{task_id}/record-run")
async def record_scheduler_run(
    task_id: str,
):
    try:
        schedule = service.record_run(
            task_id
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": str(exc),
                "task_id": task_id,
            },
        ) from exc

    return {
        "schedule": dict(schedule),
        "message": "Automation run recorded successfully.",
    }
