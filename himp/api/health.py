"""
Health API.

Provides current health status and plugin health execution.
"""

from fastapi import APIRouter, HTTPException

from himp.services.health import HealthService


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


service = HealthService()


@router.get("")
@router.get("/")
async def health_summary():

    summary = service.summary()

    return {
        "source": "PLUGIN",
        "label": "Plugin Health",
        "score": summary.score,
        "passed": summary.passed,
        "warnings": summary.warnings,
        "failed": summary.failed,
        "unknown": summary.unknown,
        "plugins": [
            {
                "plugin": plugin.plugin,
                "status": plugin.status.value,
                "message": plugin.message,
                "duration_ms": plugin.duration_ms,
                "details": plugin.details,
            }
            for plugin in summary.plugins
        ],
    }


@router.get("/all")
async def health_all():

    return service.all()


@router.get("/{plugin}")
async def health_plugin(
    plugin: str,
):

    result = service.plugin(plugin)

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Health plugin not found",
        )

    return result
