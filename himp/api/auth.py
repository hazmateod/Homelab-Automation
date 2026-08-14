"""
Authentication API.

Provides login, current-session, and logout endpoints.
"""

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from himp.api.dependencies import (
    SESSION_COOKIE_NAME,
    authenticate_request,
    require_session,
)
from himp.services.authentication import AuthenticationService
from himp.services.sessions import SessionService
from himp.lib.security_events import (
    LOGOUT,
    log_security_event,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

authentication_service = AuthenticationService()
session_service = SessionService()


class LoginRequest(BaseModel):
    username: str
    password: str


def _session_token(request):
    return request.cookies.get(
        SESSION_COOKIE_NAME
    )


@router.post("/login")
async def login(
    request: Request,
    login_request: LoginRequest,
    response: Response,
):
    result = authentication_service.authenticate(
        login_request.username,
        login_request.password,
    )

    if not result.success:
        status_code = (
            403
            if result.reason == "Account locked"
            else 401
        )

        raise HTTPException(
            status_code=status_code,
            detail=result.reason,
        )

    session = session_service.create_session(
        result.username
    )

    if not session.success:
        raise HTTPException(
            status_code=500,
            detail="Unable to create authentication session",
        )

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=int(
            SessionService.SESSION_LIFETIME.total_seconds()
        ),
    )

    return {
        "username": result.username,
        "role": result.role,
        "display_name": result.display_name,
        "password_change_required": (
            result.password_change_required
        ),
        "expires_at": (
            session.expires_at.isoformat()
            if session.expires_at is not None
            else None
        ),
    }


@router.get("/me")
async def current_user(
    request: Request,
):

    session = authenticate_request(
        request,
        session_service,
    )

    return {
        "username": session.username,
        "role": session.role,
        "created_at": (
            session.created_at.isoformat()
            if session.created_at is not None
            else None
        ),
        "expires_at": (
            session.expires_at.isoformat()
            if session.expires_at is not None
            else None
        ),
        "last_seen_at": (
            session.last_seen_at.isoformat()
            if session.last_seen_at is not None
            else None
        ),
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
):
    token = _session_token(request)

    if token:
        session_service.revoke_session(token)

    log_security_event(
        LOGOUT,
        outcome="success",
    )

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
    )

    return {
        "success": True,
        "message": "Logged out successfully.",
    }
