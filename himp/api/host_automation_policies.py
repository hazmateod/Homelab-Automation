"""
Host Automation Policy API.

Administrator-controlled automation exclusions for inventory hosts.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from himp.api.dependencies import require_admin, require_session
from himp.database.host_automation_policies import (
    HostAutomationPolicyRepository,
)
from himp.services.inventory import InventoryService


router = APIRouter(
    prefix="/inventory/hosts",
    tags=["Host Automation Policies"],
)


class HostAutomationPolicyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    reason: str = ""


def require_known_host(hostname):
    inventory = InventoryService()

    if inventory.find_host(hostname) is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory host not found",
        )


@router.get("/{hostname}/automation-policy")
async def get_host_automation_policy(
    hostname: str,
    session=Depends(require_session),
):
    require_known_host(hostname)

    repository = HostAutomationPolicyRepository()

    return repository.get(hostname)


@router.put("/{hostname}/automation-policy")
async def update_host_automation_policy(
    hostname: str,
    request: HostAutomationPolicyUpdate,
    admin=Depends(require_admin),
):
    require_known_host(hostname)

    repository = HostAutomationPolicyRepository()

    try:
        policy = repository.set_policy(
            hostname=hostname,
            enabled=request.enabled,
            reason=request.reason,
            changed_by=admin.username,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return {
        "policy": policy,
        "message": (
            "Host automation enabled"
            if policy["enabled"]
            else "Host automation disabled"
        ),
    }


@router.get("/{hostname}/automation-policy/history")
async def get_host_automation_policy_history(
    hostname: str,
    admin=Depends(require_admin),
):
    require_known_host(hostname)

    repository = HostAutomationPolicyRepository()

    return {
        "hostname": hostname,
        "history": repository.history(hostname),
    }
