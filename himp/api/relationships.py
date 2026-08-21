"""
Infrastructure Relationships API.
"""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from himp.api.dependencies import require_admin
from himp.services.asset_relationships import (
    AssetRelationshipService,
)


router = APIRouter(
    tags=["Infrastructure Relationships"],
)

relationship_service = (
    AssetRelationshipService()
)


def serialize_relationships(
    relationships,
):
    return [
        asdict(item)
        for item in relationships
    ]


@router.get("/relationships")
def infrastructure_relationships():
    relationships = (
        relationship_service.list()
    )

    return JSONResponse(
        {
            "count": len(relationships),
            "relationships": (
                serialize_relationships(
                    relationships
                )
            ),
        }
    )


@router.get(
    "/relationships/source/"
    "{source_type}/{source_id}"
)
def relationships_for_source(
    source_type: str,
    source_id: str,
):
    try:
        relationships = (
            relationship_service.list_for_source(
                source_type=source_type,
                source_id=source_id,
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return JSONResponse(
        {
            "source_type": source_type.lower(),
            "source_id": source_id,
            "count": len(relationships),
            "relationships": (
                serialize_relationships(
                    relationships
                )
            ),
        }
    )


@router.get(
    "/relationships/target/"
    "{target_type}/{target_id}"
)
def relationships_for_target(
    target_type: str,
    target_id: str,
):
    try:
        relationships = (
            relationship_service.list_for_target(
                target_type=target_type,
                target_id=target_id,
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return JSONResponse(
        {
            "target_type": target_type.lower(),
            "target_id": target_id,
            "count": len(relationships),
            "relationships": (
                serialize_relationships(
                    relationships
                )
            ),
        }
    )


@router.post("/relationships/reconcile")
def reconcile_relationships(
    _admin=Depends(require_admin),
):
    try:
        result = (
            relationship_service.reconcile()
        )

    except (
        FileNotFoundError,
        ValueError,
    ) as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    result["relationships"] = (
        serialize_relationships(
            result["relationships"]
        )
    )

    return JSONResponse(result)
