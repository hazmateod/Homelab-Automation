"""
Health Trends API.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from himp.services.health_trends import HealthTrendsService


router = APIRouter()

trends = HealthTrendsService()


@router.get("/health/trends")
def health_trends():

    return JSONResponse(
        trends.summary()
    )


@router.get("/health/trends/{plugin}")
def plugin_health_trends(
    plugin: str,
):

    result = trends.plugin(plugin)

    return JSONResponse(
        result
        if result is not None
        else {}
    )
