"""
HIMP security-event logging.

Provides a small, controlled interface for recording security
events without allowing sensitive authentication material to enter
structured log records.
"""

import logging


logger = logging.getLogger("himp.security")


LOGIN_SUCCESS = "LOGIN_SUCCESS"
LOGIN_FAILURE = "LOGIN_FAILURE"
ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
LOGOUT = "LOGOUT"
AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
SESSION_REVOKED = "SESSION_REVOKED"
PASSWORD_CHANGED = "PASSWORD_CHANGED"
PASSWORD_RESET = "PASSWORD_RESET"


_ALLOWED_EVENTS = frozenset(
    {
        LOGIN_SUCCESS,
        LOGIN_FAILURE,
        ACCOUNT_LOCKED,
        LOGOUT,
        AUTHORIZATION_DENIED,
        SESSION_REVOKED,
        PASSWORD_CHANGED,
        PASSWORD_RESET,
    }
)


def log_security_event(
    event,
    *,
    username=None,
    outcome=None,
    reason=None,
    role=None,
):
    """
    Record a security event using controlled structured fields.

    Only explicitly supported fields are accepted. Authentication
    secrets, session tokens, password hashes, and other arbitrary
    caller-provided fields cannot be added to the log record.
    """
    if event not in _ALLOWED_EVENTS:
        raise ValueError(
            f"Unsupported security event: {event}"
        )

    extra = {
        "event": event,
    }

    if username is not None:
        extra["username"] = username

    if outcome is not None:
        extra["outcome"] = outcome

    if reason is not None:
        extra["reason"] = reason

    if role is not None:
        extra["role"] = role

    logger.info(
        "Security event: %s",
        event,
        extra=extra,
    )
