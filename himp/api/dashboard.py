"""
Dashboard API.
"""

from fastapi import APIRouter, Depends

from himp.api.dependencies import require_session
from himp.services.dashboard import DashboardService


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


service = DashboardService()


@router.get("")
async def dashboard_summary(
    _user=Depends(require_session),
):

    return service.summary()


@router.get("/")
async def dashboard_summary_slash(
    _user=Depends(require_session),
):

    return service.summary()
