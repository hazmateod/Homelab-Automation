"""
Discovery API.

Provides normalized discovery information.
"""

from __future__ import annotations

from fastapi import APIRouter

from himp.services.discovery import DiscoveryService


router = APIRouter(
    prefix="/discovery",
    tags=["Discovery"],
)


service = DiscoveryService()


@router.get("/")
async def discovery_summary():

    return {
        "records": service.count(),
    }


@router.get("/records")
async def discovery_records():

    return {
        "count": service.count(),
        "records": [
            dict(record)
            for record in service.all()
        ],
    }


@router.get("/plugin/{plugin}")
async def discovery_plugin(
    plugin: str,
):

    records = service.plugin(plugin)

    return {
        "plugin": plugin,
        "count": len(records),
        "records": [
            dict(record)
            for record in records
        ],
    }


@router.get("/host/{hostname}")
async def discovery_host(
    hostname: str,
):

    records = service.host(hostname)

    return {
        "hostname": hostname,
        "count": len(records),
        "records": [
            dict(record)
            for record in records
        ],
    }
