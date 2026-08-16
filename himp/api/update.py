"""
Update API.

Provides host and group maintenance/update execution.
"""

from fastapi import APIRouter, HTTPException

from himp.app import HIMP
from himp.services.inventory import InventoryService
from himp.services.update import UpdateService


router = APIRouter(
    prefix="/update",
    tags=["Update"],
)


inventory = InventoryService()
updates = UpdateService()
himp = HIMP()


@router.post("/host/{hostname}")
async def update_host(hostname: str):
    host = inventory.find_host(hostname)

    if host is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Host not found",
                "hostname": hostname,
            },
        )

    return himp.automation.run(
        "update_host",
        limit=hostname,
        confirmed=True,
    )


@router.post("/group/{group}")
async def update_group(group: str):
    summary = inventory.summary()

    groups = {
        item.name
        for item in summary.statistics.group_counts
    }

    if group not in groups:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Inventory group not found",
                "group": group,
            },
        )

    return himp.automation.run(
        "update_group",
        limit=group,
        confirmed=True,
    )
