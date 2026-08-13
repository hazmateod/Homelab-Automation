"""
Session Service.

Provides secure server-side session creation, authentication,
refresh, and revocation without persisting plaintext tokens.
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from himp.database.sessions import SessionRepository
from himp.database.users import UserRepository


@dataclass(frozen=True)
class SessionResult:
    success: bool
    token: str | None = None
    username: str | None = None
    role: str | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None
    last_seen_at: datetime | None = None
    reason: str | None = None


class SessionService:
    """Manages secure server-side authentication sessions."""

    SESSION_LIFETIME = timedelta(hours=8)
    TOKEN_BYTES = 32

    def __init__(
        self,
        repository=None,
        users=None,
    ):
        self.repository = (
            repository
            if repository is not None
            else SessionRepository()
        )

        self.users = (
            users
            if users is not None
            else UserRepository()
        )

    def create_session(self, username, now=None):
        """Create a new session and return its plaintext token once."""
        if not isinstance(username, str):
            return SessionResult(
                success=False,
                reason="Invalid username",
            )

        username = username.strip().lower()

        if not username:
            return SessionResult(
                success=False,
                reason="Invalid username",
            )

        if now is None:
            now = self._now()

        token = secrets.token_urlsafe(
            self.TOKEN_BYTES
        )

        token_hash = self._hash_token(token)
        expires_at = (
            now + self.SESSION_LIFETIME
        )

        self.repository.create(
            token_hash,
            username,
            now,
            expires_at,
        )

        return SessionResult(
            success=True,
            token=token,
            username=username,
            created_at=now,
            expires_at=expires_at,
            last_seen_at=now,
        )

    def authenticate_session(self, token, now=None):
        """
        Authenticate a session token.

        The plaintext token is hashed before it is ever passed
        to the persistence layer. The current user record is then
        checked so account deactivation and role changes take
        effect immediately.
        """
        if not isinstance(token, str):
            return SessionResult(
                success=False,
                reason="Invalid session",
            )

        if not token:
            return SessionResult(
                success=False,
                reason="Invalid session",
            )

        if now is None:
            now = self._now()

        token_hash = self._hash_token(token)

        session = self.repository.active(
            token_hash,
            now,
        )

        if session is None:
            return SessionResult(
                success=False,
                reason="Invalid session",
            )

        user = self.users.get(
            session["username"]
        )

        if user is None:
            return SessionResult(
                success=False,
                reason="Invalid session",
            )

        if not user.active:
            return SessionResult(
                success=False,
                reason="Invalid session",
            )

        self.repository.touch(
            token_hash,
            now,
        )

        return SessionResult(
            success=True,
            username=session["username"],
            role=user.role,
            created_at=session["created_at"],
            expires_at=session["expires_at"],
            last_seen_at=now,
        )

    def revoke_session(self, token, now=None):
        """Revoke a single session."""
        if not isinstance(token, str) or not token:
            return False

        if now is None:
            now = self._now()

        token_hash = self._hash_token(token)

        self.repository.revoke(
            token_hash,
            now,
        )

        return True

    def revoke_all_sessions(self, username, now=None):
        """Revoke every session belonging to a user."""
        if not isinstance(username, str):
            return False

        username = username.strip().lower()

        if not username:
            return False

        if now is None:
            now = self._now()

        self.repository.revoke_all(
            username,
            now,
        )

        return True

    def cleanup(self, now=None):
        """Delete expired and revoked sessions."""
        if now is None:
            now = self._now()

        return self.repository.delete_expired(
            now
        )

    @staticmethod
    def _hash_token(token):
        return hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _now():
        return datetime.now(
            timezone.utc
        ).replace(tzinfo=None)
