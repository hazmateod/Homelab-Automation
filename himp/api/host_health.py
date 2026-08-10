"""
Host Health API.

Provides current host health, infrastructure health summaries,
and persisted host health history.
"""

from fastapi import APIRouter, HTTPException, Query

from himp.services.host_health import HostHealthService
from himp.services.host_health_dashboard import HostHealthDashboardService


router = APIRouter(
    prefix="/health/hosts",
    tags=["Host Health"],
)


dashboard = HostHealthDashboardService()
health = HostHealthService()


@router.get("")
@router.get("/")
def host_health_summary():

    return dashboard.summary()


@router.get("/history")
def host_health_history(
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
    ),
):

    return {
        "history": dashboard.health.history(
            limit=limit,
        ),
    }


@router.get("/trends")
def host_health_trends(
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
    ),
):

    return {
        "trends": dashboard.trends(
            limit=limit,
        ),
    }


@router.get("/{hostname}")
def host_health_host(
    hostname: str,
):

    hosts = dashboard.hosts()

    for host in hosts:

        if host["hostname"] == hostname:

            return host

    raise HTTPException(
        status_code=404,
        detail="Inventory host not found",
    )


@router.get("/{hostname}/history")
def host_health_host_history(
    hostname: str,
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
    ),
):

    inventory_host = dashboard.inventory.find_host(
        hostname,
    )

    if inventory_host is None:

        raise HTTPException(
            status_code=404,
            detail="Inventory host not found",
        )

    return {
        "hostname": hostname,
        "history": health.history(
            hostname=hostname,
            limit=limit,
        ),
    }
