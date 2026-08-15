import pytest

from himp.services.user_management import (
    UserManagementService,
)


class FakeRepository:
    def __init__(self):
        self.users = {
            "admin": {
                "username": "admin",
                "role": "admin",
                "active": True,
                "display_name": "Administrator",
            },
        }

    def normalize_username(self, username):
        if not isinstance(username, str):
            raise TypeError("Username must be a string")

        username = username.strip().lower()

        if not username:
            raise ValueError("Username cannot be empty")

        return username

    def all(self):
        return list(self.users.values())

    def get(self, username):
        return self.users.get(username)

    def create(
        self,
        username,
        password_hash,
        role,
        display_name="",
        password_change_required=False,
    ):
        if username in self.users:
            raise ValueError("User already exists")

        self.users[username] = {
            "username": username,
            "role": role,
            "active": True,
            "display_name": display_name,
            "password_hash": password_hash,
            "password_change_required": password_change_required,
        }

        return self.get(username)

    def set_active(self, username, active):
        self.users[username]["active"] = active

    def set_role(self, username, role):
        self.users[username]["role"] = role

    def set_display_name(self, username, display_name):
        self.users[username]["display_name"] = display_name


class FakePasswords:
    def hash(self, password):
        return f"hashed:{password}"


class FakePolicyResult:
    def __init__(self, valid, reason=None):
        self.valid = valid
        self.reason = reason


class FakePolicy:
    def validate(self, password):
        return FakePolicyResult(valid=bool(password))


def test_list_users_returns_users_without_password_hashes():
    service = UserManagementService(
        repository=FakeRepository(),
        passwords=FakePasswords(),
        policy=FakePolicy(),
    )

    users = service.list_users()

    assert users == [
        {
            "username": "admin",
            "role": "admin",
            "active": True,
            "display_name": "Administrator",
        }
    ]


def test_create_user_normalizes_username_hashes_password_and_returns_user():
    repository = FakeRepository()

    service = UserManagementService(
        repository=repository,
        passwords=FakePasswords(),
        policy=FakePolicy(),
    )

    result = service.create_user(
        username="  Operator1  ",
        password="valid-password",
        role="operator",
        display_name="Operator One",
    )

    assert result["username"] == "operator1"
    assert result["role"] == "operator"
    assert result["active"] is True
    assert result["display_name"] == "Operator One"
    assert repository.users["operator1"]["password_hash"] == (
        "hashed:valid-password"
    )


def test_create_user_rejects_invalid_password():
    service = UserManagementService(
        repository=FakeRepository(),
        passwords=FakePasswords(),
        policy=FakePolicy(),
    )

    with pytest.raises(ValueError, match="Password"):
        service.create_user(
            username="operator1",
            password="",
            role="operator",
        )


def test_set_active_updates_user_state():
    repository = FakeRepository()

    service = UserManagementService(
        repository=repository,
        passwords=FakePasswords(),
        policy=FakePolicy(),
    )

    result = service.set_active("admin", False)

    assert result["active"] is False
    assert repository.users["admin"]["active"] is False


def test_set_role_updates_user_role():
    repository = FakeRepository()

    service = UserManagementService(
        repository=repository,
        passwords=FakePasswords(),
        policy=FakePolicy(),
    )

    result = service.set_role("admin", "operator")

    assert result["role"] == "operator"


def test_set_display_name_updates_user():
    repository = FakeRepository()

    service = UserManagementService(
        repository=repository,
        passwords=FakePasswords(),
        policy=FakePolicy(),
    )

    result = service.set_display_name(
        "admin",
        "New Administrator",
    )

    assert result["display_name"] == "New Administrator"
