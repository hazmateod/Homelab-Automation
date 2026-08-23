"""
Maintenance Window API.

Provides maintenance-window visibility and administrator mutation
operations.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from himp.api.dependencies import require_admin
from himp.services.maintenance_windows import (
    MaintenanceWindowService,
)


class MaintenanceWindowCreate(BaseModel):
    name: str
    reason: str
    starts_at: datetime
    ends_at: datetime
    task_id: str | None = None
    enabled: bool = True


class MaintenanceWindowEnabledUpdate(BaseModel):
    enabled: bool


router = APIRouter(
    prefix="/maintenance-windows",
    tags=["Maintenance Windows"],
)

service = MaintenanceWindowService()


@router.get("")
@router.get("/")
async def maintenance_window_summary():
    return {
        **service.list(),
        "active": service.active_all(),
        "upcoming": service.upcoming(),
    }


@router.get("/{window_id}")
async def maintenance_window_detail(
    window_id: int,
):
    try:
        return service.get(window_id)

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": str(exc),
                "window_id": window_id,
            },
        ) from exc


@router.post(
    "",
    dependencies=[Depends(require_admin)],
)
@router.post(
    "/",
    dependencies=[Depends(require_admin)],
)
async def create_maintenance_window(
    request: MaintenanceWindowCreate,
    admin=Depends(require_admin),
):
    try:
        window = service.create(
            name=request.name,
            reason=request.reason,
            starts_at=request.starts_at,
            ends_at=request.ends_at,
            task_id=request.task_id,
            enabled=request.enabled,
            created_by=admin.username,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": str(exc),
            },
        ) from exc

    return {
        "window": window,
        "message": "Maintenance window created successfully.",
    }


@router.put(
    "/{window_id}/enabled",
    dependencies=[Depends(require_admin)],
)
async def update_maintenance_window_enabled(
    window_id: int,
    request: MaintenanceWindowEnabledUpdate,
):
    try:
        window = service.set_enabled(
            window_id=window_id,
            enabled=request.enabled,
        )

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": str(exc),
                "window_id": window_id,
            },
        ) from exc

    return {
        "window": window,
        "message": "Maintenance window state updated successfully.",
    }
