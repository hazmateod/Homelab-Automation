"""
{{ display_name }} API.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(
    prefix="/{{ name }}",
    tags=["{{ display_name }}"],
)


@router.get("/")
async def list_{{ name }}():
    """
    List {{ display_name }} resources.
    """

    return {
        "service": "{{ class_name }}",
        "status": "ok",
        "items": [],
    }
