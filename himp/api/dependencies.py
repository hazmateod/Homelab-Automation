"""
FastAPI authentication and authorization dependencies.

Provides reusable request authentication and authorization
for protected HIMP API and web endpoints.
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


def require_admin(request: Request):
    """Require an authenticated administrator session."""
    session = require_session(request)

    if session.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Administrator access required",
        )

    return session


def require_page_session(request: Request):
    """
    Require an authenticated browser session.

    Browser navigation receives a redirect to the login page
    instead of an API-style JSON 401 response.
    """
    try:
        return require_session(request)
    except HTTPException as error:
        if error.status_code == 401:
            raise HTTPException(
                status_code=303,
                detail="Authentication required",
                headers={
                    "Location": "/login"
                },
            )

        raise
