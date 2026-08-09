"""
Inventory API.

Provides inventory and CMDB information.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from himp.database.inventory import InventoryRepository
from himp.services.inventory import InventoryService


class InventoryHostCreate(BaseModel):
    hostname: str
    group: str
    ip: str
    user: str
    become: bool = False


class InventoryHostUpdate(BaseModel):
    group: str
    ip: str
    user: str
    become: bool = False


router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"],
)


service = InventoryService()
repository = InventoryRepository()


@router.get("")
@router.get("/")
async def inventory_summary():
    return service.summary()


@router.get("/statistics")
async def inventory_statistics():
    summary = service.summary()

    return summary.statistics


@router.get("/groups")
async def inventory_groups():
    summary = service.summary()

    return {
        "groups": summary.statistics.group_counts,
        "count": summary.statistics.groups,
    }


@router.get("/hosts")
async def inventory_hosts():
    return {
        "count": repository.count(),
        "hosts": repository.all_hosts(),
    }


@router.post("/hosts")
async def create_inventory_host(
    request: InventoryHostCreate,
):
    try:
        host = service.add_host(
            hostname=request.hostname,
            group=request.group,
            ip=request.ip,
            user=request.user,
            become=request.become,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": str(exc),
                "hostname": request.hostname,
            },
        ) from exc

    return {
        "host": dict(host),
        "message": "Inventory host created successfully.",
    }


@router.put("/hosts/{hostname}")
async def update_inventory_host(
    hostname: str,
    request: InventoryHostUpdate,
):
    try:
        host = service.update_host(
            hostname=hostname,
            group=request.group,
            ip=request.ip,
            user=request.user,
            become=request.become,
        )

    except ValueError as exc:
        message = str(exc)

        if message.startswith("Inventory host does not exist:"):
            status_code = 404
        else:
            status_code = 400

        raise HTTPException(
            status_code=status_code,
            detail={
                "error": message,
                "hostname": hostname,
            },
        ) from exc

    return {
        "host": dict(host),
        "message": "Inventory host updated successfully.",
    }


@router.delete("/hosts/{hostname}")
async def delete_inventory_host(
    hostname: str,
):
    try:
        host = service.remove_host(
            hostname=hostname,
        )

    except ValueError as exc:
        message = str(exc)

        if message.startswith("Inventory host does not exist:"):
            status_code = 404
        else:
            status_code = 400

        raise HTTPException(
            status_code=status_code,
            detail={
                "error": message,
                "hostname": hostname,
            },
        ) from exc

    return {
        "host": dict(host),
        "message": "Inventory host removed successfully.",
    }


@router.get("/hosts/{hostname}")
async def inventory_host(
    hostname: str,
):
    host = repository.find_host(
        hostname
    )

    if host is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Host not found",
                "hostname": hostname,
            },
        )

    return host


@router.get("/cmdb")
async def cmdb():
    return {
        "hosts": repository.all_hosts(),
        "count": repository.count(),
    }


@router.get("/changes")
async def changes():
    return {
        "changes": repository.changes(),
    }


@router.get("/sync")
async def sync_inventory():
    return service.sync()
