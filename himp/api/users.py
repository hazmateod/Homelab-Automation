"""
User Management API.

Provides administrator-only user management endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from himp.services.user_management import UserManagementService


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

user_management = UserManagementService()


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str
    display_name: str = ""
    password_change_required: bool = False


@router.get("")
async def list_users():
    return {
        "users": user_management.list_users(),
    }


@router.post("")
async def create_user(
    request: CreateUserRequest,
):
    try:
        return user_management.create_user(
            username=request.username,
            password=request.password,
            role=request.role,
            display_name=request.display_name,
            password_change_required=(
                request.password_change_required
            ),
        )
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
