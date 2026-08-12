"""
Password Management Service.

Provides secure self-service password changes and
administrator password resets.
"""

import secrets
import string
from dataclasses import dataclass

from himp.database.users import UserRepository
from himp.services.passwords import PasswordService


@dataclass(frozen=True)
class PasswordChangeResult:
    success: bool
    username: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class PasswordResetResult:
    success: bool
    username: str | None = None
    temporary_password: str | None = None
    password_change_required: bool = False
    reason: str | None = None


class PasswordManagementService:
    """Manages user password changes and administrator resets."""

    TEMPORARY_PASSWORD_LENGTH = 20

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

    def change_password(
        self,
        username,
        current_password,
        new_password,
    ):
        """
        Change the authenticated user's password.

        The current password must be valid before any mutation
        is made to the account.
        """
        try:
            normalized = (
                self.repository.normalize_username(
                    username
                )
            )
        except (TypeError, ValueError):
            return PasswordChangeResult(
                success=False,
                reason="Invalid credentials",
            )

        credentials = self.repository.credentials(
            normalized
        )

        if credentials is None:
            return PasswordChangeResult(
                success=False,
                reason="Invalid credentials",
            )

        if not credentials["active"]:
            return PasswordChangeResult(
                success=False,
                reason="Invalid credentials",
            )

        if credentials["failed_login_attempts"] >= 5:
            return PasswordChangeResult(
                success=False,
                reason="Account locked",
            )

        if not self.passwords.verify(
            current_password,
            credentials["password_hash"],
        ):
            return PasswordChangeResult(
                success=False,
                reason="Invalid credentials",
            )

        if not isinstance(new_password, str):
            return PasswordChangeResult(
                success=False,
                reason="Invalid new password",
            )

        if not new_password:
            return PasswordChangeResult(
                success=False,
                reason="Invalid new password",
            )

        try:
            new_hash = self.passwords.hash(
                new_password
            )
        except (TypeError, ValueError):
            return PasswordChangeResult(
                success=False,
                reason="Invalid new password",
            )

        self.repository.set_password(
            normalized,
            new_hash,
            password_change_required=False,
        )

        return PasswordChangeResult(
            success=True,
            username=normalized,
        )

    def reset_password(
        self,
        administrator,
        username,
        temporary_password=None,
    ):
        """
        Reset another user's password as an administrator.

        A generated temporary password is returned exactly once
        to the caller and is never persisted in plaintext.
        """
        administrator = self._user(
            administrator
        )

        if administrator is None:
            return PasswordResetResult(
                success=False,
                reason="Administrator authorization required",
            )

        if administrator.role != "admin":
            return PasswordResetResult(
                success=False,
                reason="Administrator authorization required",
            )

        try:
            normalized = (
                self.repository.normalize_username(
                    username
                )
            )
        except (TypeError, ValueError):
            return PasswordResetResult(
                success=False,
                reason="User not found",
            )

        credentials = self.repository.credentials(
            normalized
        )

        if credentials is None:
            return PasswordResetResult(
                success=False,
                reason="User not found",
            )

        if temporary_password is None:
            temporary_password = (
                self._generate_temporary_password()
            )

        try:
            password_hash = self.passwords.hash(
                temporary_password
            )
        except (TypeError, ValueError):
            return PasswordResetResult(
                success=False,
                reason="Invalid temporary password",
            )

        self.repository.set_password(
            normalized,
            password_hash,
            password_change_required=True,
        )

        return PasswordResetResult(
            success=True,
            username=normalized,
            temporary_password=temporary_password,
            password_change_required=True,
        )

    def _user(self, username):
        try:
            normalized = (
                self.repository.normalize_username(
                    username
                )
            )
        except (TypeError, ValueError):
            return None

        return self.repository.get(normalized)

    @classmethod
    def _generate_temporary_password(cls):
        alphabet = (
            string.ascii_letters
            + string.digits
            + "!@#$%^&*-_=+"
        )

        return "".join(
            secrets.choice(alphabet)
            for _ in range(
                cls.TEMPORARY_PASSWORD_LENGTH
            )
        )
