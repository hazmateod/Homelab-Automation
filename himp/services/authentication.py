"""
Authentication Service.

Provides username/password authentication, failed-login
tracking, account lockout, and password-change state.
"""

from dataclasses import dataclass

from himp.database.users import UserRepository
from himp.services.passwords import PasswordService
from himp.lib.security_events import (
    ACCOUNT_LOCKED,
    LOGIN_FAILURE,
    LOGIN_SUCCESS,
    log_security_event,
)


@dataclass(frozen=True)
class AuthenticationResult:
    success: bool
    username: str | None = None
    role: str | None = None
    display_name: str | None = None
    password_change_required: bool = False
    reason: str | None = None


class AuthenticationService:
    """Authenticates HIMP users and enforces login policy."""

    MAX_FAILED_ATTEMPTS = 5

    DUMMY_PASSWORD_HASH = (
        "$argon2id$v=19$m=65536,t=3,p=4$"
        "FWDTndJAFO862CzgpXKuGA$"
        "hUybZJ1oZCnryRByUPkd9XhxJiSe0yHNkqORHpURbXY"
    )

    def __init__(
        self,
        repository=None,
        passwords=None,
    ):
        self.repository = (
            repository
            if repository is not None
            else UserRepository()
        )

        self.passwords = (
            passwords
            if passwords is not None
            else PasswordService()
        )

    def authenticate(
        self,
        username,
        password,
    ):
        try:
            normalized = (
                self.repository.normalize_username(
                    username
                )
            )
        except (TypeError, ValueError):
            return self._failure(
                "Invalid credentials"
            )

        if not isinstance(password, str):
            log_security_event(
                LOGIN_FAILURE,
                username=normalized,
                outcome="failure",
                reason="Invalid credentials",
            )

            return self._failure(
                "Invalid credentials"
            )

        credentials = self.repository.credentials(
            normalized
        )

        if credentials is None:
            self.passwords.verify(
                password,
                self.DUMMY_PASSWORD_HASH,
            )

            log_security_event(
                LOGIN_FAILURE,
                username=normalized,
                outcome="failure",
                reason="Invalid credentials",
            )

            return self._failure(
                "Invalid credentials"
            )

        password_hash = credentials["password_hash"]

        password_valid = self.passwords.verify(
            password,
            password_hash,
        )

        if not credentials["active"]:
            log_security_event(
                LOGIN_FAILURE,
                username=normalized,
                outcome="failure",
                reason="Invalid credentials",
            )

            return self._failure(
                "Invalid credentials"
            )

        if (
            credentials["failed_login_attempts"]
            >= self.MAX_FAILED_ATTEMPTS
        ):
            log_security_event(
                ACCOUNT_LOCKED,
                username=normalized,
                outcome="failure",
                reason="Account locked",
            )

            return self._failure(
                "Account locked"
            )

        if not password_valid:
            attempts = (
                credentials["failed_login_attempts"]
                + 1
            )

            self.repository.record_login_failure(
                normalized
            )

            if attempts >= self.MAX_FAILED_ATTEMPTS:
                log_security_event(
                    ACCOUNT_LOCKED,
                    username=normalized,
                    outcome="failure",
                    reason="Account locked",
                )

                return self._failure(
                    "Account locked"
                )

            log_security_event(
                LOGIN_FAILURE,
                username=normalized,
                outcome="failure",
                reason="Invalid credentials",
            )

            return self._failure(
                "Invalid credentials"
            )

        self.repository.update_login_success(
            normalized
        )

        log_security_event(
            LOGIN_SUCCESS,
            username=credentials["username"],
            outcome="success",
        )

        return AuthenticationResult(
            success=True,
            username=credentials["username"],
            role=credentials["role"],
            display_name=credentials["display_name"],
            password_change_required=bool(
                credentials[
                    "password_change_required"
                ]
            ),
        )

    @staticmethod
    def _failure(reason):
        return AuthenticationResult(
            success=False,
            reason=reason,
        )
