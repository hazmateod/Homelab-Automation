"""
User Management Service.

Provides administrative operations over HIMP users while
reusing the existing user repository, password hashing,
and password policy infrastructure.
"""

from himp.database.users import UserRepository
from himp.services.password_policy import PasswordPolicyService
from himp.services.passwords import PasswordService


class UserManagementService:
    """
    Administrative user-management operations.
    """

    def __init__(
        self,
        repository=None,
        passwords=None,
        policy=None,
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
        self.policy = (
            policy
            if policy is not None
            else PasswordPolicyService()
        )

    def list_users(self):
        return [
            self._public_user(user)
            for user in self.repository.all()
        ]

    def create_user(
        self,
        username,
        password,
        role,
        display_name="",
        password_change_required=False,
    ):
        username = self.repository.normalize_username(
            username
        )

        validation = self.policy.validate(password)

        if not validation.valid:
            raise ValueError(
                validation.reason or "Password is invalid"
            )

        password_hash = self.passwords.hash(password)

        user = self.repository.create(
            username=username,
            password_hash=password_hash,
            role=role,
            display_name=display_name,
            password_change_required=(
                password_change_required
            ),
        )

        return self._public_user(user)

    def set_active(self, username, active):
        self.repository.set_active(
            username,
            active,
        )

        return self._require_user(username)

    def set_role(self, username, role):
        self.repository.set_role(
            username,
            role,
        )

        return self._require_user(username)

    def set_display_name(
        self,
        username,
        display_name,
    ):
        self.repository.set_display_name(
            username,
            display_name,
        )

        return self._require_user(username)

    def _require_user(self, username):
        user = self.repository.get(username)

        if user is None:
            raise ValueError(
                f"User not found: {username}"
            )

        return self._public_user(user)

    @staticmethod
    def _public_user(user):
        if isinstance(user, dict):
            return {
                key: value
                for key, value in user.items()
                if key != "password_hash"
            }

        return {
            "username": user.username,
            "role": user.role,
            "active": user.active,
            "display_name": user.display_name,
            "password_change_required": (
                user.password_change_required
            ),
        }
