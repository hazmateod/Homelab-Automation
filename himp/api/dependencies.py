"""
FastAPI authentication dependencies.

Provides reusable request authentication for protected
HIMP API endpoints.
"""

from fastapi import HTTPException, Request

from himp.services.sessions import SessionService


SESSION_COOKIE_NAME = "himp_session"

session_service = SessionService()


def authenticate_request(
    request: Request,
    session_service_instance,
):
    """
    Authenticate a request using the supplied session service.

    Raises HTTP 401 when the request does not contain a
    valid active HIMP session.
    """
    token = request.cookies.get(
        SESSION_COOKIE_NAME
    )

    result = session_service_instance.authenticate_session(
        token
    )

    if not result.success:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    return result


def require_session(request: Request):
    """Return the authenticated session for protected API routes."""
    return authenticate_request(
        request,
        session_service,
    )
