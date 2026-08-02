"""
Inventory API.

Provides inventory and CMDB information.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from himp.services.inventory import InventoryService
from himp.database.inventory import InventoryRepository


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
