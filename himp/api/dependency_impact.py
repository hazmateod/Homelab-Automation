"""
Infrastructure Dependency and Impact Analysis API.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from himp.services.dependency_impact import (
    DependencyImpactService,
)


router = APIRouter(
    tags=["Infrastructure Dependency & Impact"],
)

dependency_impact_service = (
    DependencyImpactService()
)


@router.get(
    "/dependencies/{entity_type}/{entity_id}"
)
def infrastructure_dependencies(
    entity_type: str,
    entity_id: str,
    max_depth: int | None = Query(
        default=None,
        ge=1,
    ),
):
    try:
        result = (
            dependency_impact_service.dependencies(
                entity_type=entity_type,
                entity_id=entity_id,
                max_depth=max_depth,
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return JSONResponse(
        result
    )


@router.get(
    "/impact/{entity_type}/{entity_id}"
)
def infrastructure_impact(
    entity_type: str,
    entity_id: str,
    max_depth: int | None = Query(
        default=None,
        ge=1,
    ),
):
    try:
        result = (
            dependency_impact_service.impact(
                entity_type=entity_type,
                entity_id=entity_id,
                max_depth=max_depth,
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return JSONResponse(
        result
    )
