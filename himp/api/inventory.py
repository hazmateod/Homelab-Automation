"""
Inventory API.

Provides inventory and CMDB information.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from himp.database.inventory import InventoryRepository
from himp.services.host_health import HostHealthService
from himp.services.inventory import InventoryService
from himp.services.ssh import SSHService
from himp.services.storage_capacity import StorageCapacityService


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


class InventoryGroupUpdate(BaseModel):
    new_group: str


router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"],
)


service = InventoryService()
repository = InventoryRepository()
ssh_service = SSHService()
host_health_service = HostHealthService()
storage_service = StorageCapacityService()


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


@router.put("/groups/{group}")
async def update_inventory_group(
    group: str,
    request: InventoryGroupUpdate,
):
    try:
        result = service.rename_group(
            group=group,
            new_group=request.new_group,
        )

    except ValueError as exc:
        message = str(exc)

        if message.startswith(
            "Inventory group does not exist:"
        ):
            status_code = 404
        elif message.startswith(
            "Inventory group already exists:"
        ):
            status_code = 409
        else:
            status_code = 400

        raise HTTPException(
            status_code=status_code,
            detail={"error": message},
        ) from exc

    return {
        "group": result,
        "message": "Inventory group updated successfully.",
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


@router.post("/hosts/{hostname}/restore")
async def restore_inventory_host(
    hostname: str,
):
    try:
        host = service.restore_host(
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
        "message": "Inventory host restored successfully.",
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


@router.post("/hosts/{hostname}/ssh-test")
async def test_inventory_host_ssh(
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

    result = ssh_service.test(
        hostname=host["hostname"],
        ip=host["ip"],
        user=host["ansible_user"],
    )

    return {
        "hostname": result.hostname,
        "ip": result.ip,
        "user": result.user,
        "status": result.status,
        "success": result.success,
        "return_code": result.return_code,
        "elapsed": result.elapsed,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "message": result.message,
    }


@router.post("/hosts/{hostname}/health")
async def check_inventory_host_health(
    hostname: str,
):
    try:
        result = host_health_service.check_host(
            hostname
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": str(exc),
                "hostname": hostname,
            },
        ) from exc

    return result


@router.get("/hosts/{hostname}/health")
async def inventory_host_health(
    hostname: str,
):
    result = host_health_service.latest(
        hostname
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Host health result not found",
                "hostname": hostname,
            },
        )

    return result


@router.get("/hosts/{hostname}/health/history")
async def inventory_host_health_history(
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

    history = host_health_service.history(
        hostname
    )

    return {
        "hostname": hostname,
        "count": len(history),
        "history": history,
    }


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

@router.get("/hosts/{hostname}/storage")
async def inventory_host_storage(
    hostname: str,
):
    try:
        return storage_service.host(
            hostname
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": str(exc),
                "hostname": hostname,
            },
        ) from exc


@router.get("/storage")
async def inventory_storage_summary():
    return storage_service.summary()
