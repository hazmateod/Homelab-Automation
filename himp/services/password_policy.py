"""
Password Policy Service.

Provides centralized validation for HIMP passwords.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordPolicyResult:
    valid: bool
    reason: str | None = None


class PasswordPolicyService:
    """Validates passwords against the HIMP password policy."""

    MIN_LENGTH = 12
    MAX_LENGTH = 128

    def validate(self, password):
        if not isinstance(password, str):
            return PasswordPolicyResult(
                valid=False,
                reason="Password must be a string",
            )

        if not password.strip():
            return PasswordPolicyResult(
                valid=False,
                reason="Password cannot be empty",
            )

        if len(password) < self.MIN_LENGTH:
            return PasswordPolicyResult(
                valid=False,
                reason=(
                    f"Password must be at least "
                    f"{self.MIN_LENGTH} characters"
                ),
            )

        if len(password) > self.MAX_LENGTH:
            return PasswordPolicyResult(
                valid=False,
                reason=(
                    f"Password cannot exceed "
                    f"{self.MAX_LENGTH} characters"
                ),
            )

        return PasswordPolicyResult(valid=True)
