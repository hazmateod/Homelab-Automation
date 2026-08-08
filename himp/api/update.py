"""
Update API.

Provides host and group maintenance/update execution.
"""

from fastapi import APIRouter, HTTPException

from himp.config import config
from himp.lib.ansible import run_playbook
from himp.services.inventory import InventoryService


router = APIRouter(
    prefix="/update",
    tags=["Update"],
)

inventory = InventoryService()


def _run_update(target):
    success, elapsed = run_playbook(
        config.maintenance_playbook,
        target,
    )

    return {
        "target": target,
        "success": success,
        "elapsed": round(elapsed, 3),
    }


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

    return _run_update(hostname)


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

    return _run_update(group)
