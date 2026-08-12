"""
Password Service.

Provides secure password hashing and verification using Argon2id.
"""

from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHash,
    VerificationError,
    VerifyMismatchError,
)


class PasswordService:
    """Provides secure password hashing and verification."""

    def __init__(self):
        self.hasher = PasswordHasher()

    def hash(self, password):
        """Return an Argon2id hash for the supplied password."""
        if not isinstance(password, str):
            raise TypeError("Password must be a string")

        if not password:
            raise ValueError("Password cannot be empty")

        return self.hasher.hash(password)

    def verify(self, password, password_hash):
        """Return True when the password matches the supplied hash."""
        if not isinstance(password, str):
            return False

        if not isinstance(password_hash, str):
            return False

        try:
            return self.hasher.verify(
                password_hash,
                password,
            )
        except (
            InvalidHash,
            VerificationError,
            VerifyMismatchError,
        ):
            return False
