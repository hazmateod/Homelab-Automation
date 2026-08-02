"""
Discovery API.

Provides normalized discovery information.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from himp.services.discovery import DiscoveryService


router = APIRouter(
    prefix="/discovery",
    tags=["Discovery"],
)


service = DiscoveryService()


@router.get("")
@router.get("/")
async def discovery_summary():

    return {
        "records": service.count(),
    }


@router.get("/statistics")
async def discovery_statistics():

    records = [
        dict(record)
        for record in service.all()
    ]

    plugins = {
        record["plugin"]
        for record in records
    }

    hosts = {
        record["hostname"]
        for record in records
    }

    categories = {
        record["category"]
        for record in records
    }

    return {
        "records": len(records),
        "plugins": len(plugins),
        "hosts": len(hosts),
        "categories": len(categories),
    }


@router.get("/categories")
async def discovery_categories():

    counts = {}

    for record in service.all():

        category = record["category"]

        counts[category] = (
            counts.get(category, 0) + 1
        )

    return {
        "categories": [
            {
                "name": name,
                "records": count,
            }
            for name, count in sorted(
                counts.items()
            )
        ]
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

    if not records:

        raise HTTPException(
            status_code=404,
            detail="Discovery plugin not found",
        )

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

    if not records:

        raise HTTPException(
            status_code=404,
            detail="Discovery host not found",
        )

    return {
        "hostname": hostname,
        "count": len(records),
        "records": [
            dict(record)
            for record in records
        ],
    }
