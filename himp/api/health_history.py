"""
Health History API.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from himp.services.health_history import HealthHistoryService


router = APIRouter()

history = HealthHistoryService()


@router.get("/health/history")
def health_history():

    return JSONResponse(
        {
            "summary": history.summary(),
            "history": history.history(),
        }
    )


@router.get("/health/history/{plugin}")
def plugin_health_history(
    plugin: str,
):

    return JSONResponse(
        {
            "plugin": plugin,
            "history": history.plugin(plugin),
        }
    )
