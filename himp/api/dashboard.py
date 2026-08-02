"""
Dashboard API.
"""

from fastapi import APIRouter

from himp.services.dashboard import DashboardService


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


service = DashboardService()


@router.get("/")
async def dashboard_summary():

    return service.summary()
