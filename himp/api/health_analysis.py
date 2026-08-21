"""
Historical Health Analysis API.
"""

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from himp.services.health_analysis import (
    HealthAnalysisService,
)


router = APIRouter(
    prefix="/health/analysis",
    tags=["Health Analysis"],
)

analysis_service = (
    HealthAnalysisService()
)


@router.get("/plugins/{plugin}")
def plugin_health_analysis(
    plugin: str,
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
):
    try:
        result = analysis_service.plugin(
            plugin,
            limit=limit,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Plugin health history not found",
        )

    return result


@router.get("/hosts/{hostname}")
def host_health_analysis(
    hostname: str,
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
):
    try:
        result = analysis_service.host(
            hostname,
            limit=limit,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Host health history not found",
        )

    return result


@router.get(
    "/correlation/{entity_type}/{entity_id}"
)
def correlated_health_analysis(
    entity_type: str,
    entity_id: str,
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
):
    try:
        return analysis_service.correlate(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
