"""
Inventory Manager API.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(
    prefix="/inventory_manager",
    tags=["Inventory Manager"],
)


@router.get("/")
async def list_inventory_manager():
    """
    List Inventory Manager resources.
    """

    return {
        "service": "InventoryManager",
        "status": "ok",
        "items": [],
    }
