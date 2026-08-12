from himp.services.password_management import (
    PasswordManagementService,
)


class FakeUser:
    def __init__(
        self,
        username,
        role,
        active=True,
    ):
        self.username = username
        self.role = role
        self.active = active


class FakeRepository:
    def __init__(self):
        self.users = {
            "admin": {
                "username": "admin",
                "password_hash": "admin-hash",
                "active": True,
                "role": "admin",
                "failed_login_attempts": 0,
                "password_change_required": False,
                "display_name": "Administrator",
            },
            "operator": {
                "username": "operator",
                "password_hash": "operator-hash",
                "active": True,
                "role": "operator",
                "failed_login_attempts": 0,
                "password_change_required": False,
                "display_name": "Operator",
            },
        }

        self.password_changes = []

    @staticmethod
    def normalize_username(username):
        if not isinstance(username, str):
            raise TypeError

        username = username.strip().lower()

        if not username:
            raise ValueError

        return username

    def credentials(self, username):
        return self.users.get(username)

    def get(self, username):
        user = self.users.get(username)

        if user is None:
            return None

        return FakeUser(
            username=user["username"],
            role=user["role"],
            active=user["active"],
        )

    def set_password(
        self,
        username,
        password_hash,
        password_change_required=False,
    ):
        self.users[username]["password_hash"] = (
            password_hash
        )

        self.users[username][
            "password_change_required"
        ] = password_change_required

        self.users[username][
            "failed_login_attempts"
        ] = 0

        self.password_changes.append(
            (
                username,
                password_hash,
                password_change_required,
            )
        )


class FakePasswordService:
    def __init__(self):
        self.hashes = []
        self.verifications = []

    def verify(self, password, password_hash):
        self.verifications.append(
            (password, password_hash)
        )

        return (
            password == "CurrentPassword!"
            and password_hash == "admin-hash"
        )

    def hash(self, password):
        self.hashes.append(password)
        return f"hash:{password}"


def make_service():
    repository = FakeRepository()
    passwords = FakePasswordService()

    service = PasswordManagementService(
        repository=repository,
        passwords=passwords,
    )

    return service, repository, passwords


def test_user_can_change_own_password():
    service, repository, passwords = make_service()

    result = service.change_password(
        "admin",
        "CurrentPassword!",
        "NewPassword!",
    )

    assert result.success is True
    assert result.username == "admin"
    assert result.reason is None

    assert passwords.hashes == [
        "NewPassword!",
    ]

    assert repository.password_changes == [
        (
            "admin",
            "hash:NewPassword!",
            False,
        )
    ]


def test_change_password_normalizes_username():
    service, repository, _ = make_service()

    result = service.change_password(
        "  ADMIN  ",
        "CurrentPassword!",
        "NewPassword!",
    )

    assert result.success is True
    assert result.username == "admin"


def test_change_password_rejects_wrong_current_password():
    service, repository, passwords = make_service()

    result = service.change_password(
        "admin",
        "WrongPassword!",
        "NewPassword!",
    )

    assert result.success is False
    assert result.reason == "Invalid credentials"
    assert passwords.hashes == []
    assert repository.password_changes == []


def test_change_password_rejects_unknown_user():
    service, repository, passwords = make_service()

    result = service.change_password(
        "missing",
        "CurrentPassword!",
        "NewPassword!",
    )

    assert result.success is False
    assert result.reason == "Invalid credentials"
    assert passwords.hashes == []
    assert repository.password_changes == []


def test_change_password_rejects_disabled_user():
    service, repository, passwords = make_service()

    repository.users["admin"]["active"] = False

    result = service.change_password(
        "admin",
        "CurrentPassword!",
        "NewPassword!",
    )

    assert result.success is False
    assert result.reason == "Invalid credentials"
    assert passwords.hashes == []


def test_change_password_rejects_invalid_new_password():
    service, repository, passwords = make_service()

    result = service.change_password(
        "admin",
        "CurrentPassword!",
        "",
    )

    assert result.success is False
    assert result.reason == "Invalid new password"
    assert passwords.hashes == []
    assert repository.password_changes == []


def test_admin_can_reset_password():
    service, repository, passwords = make_service()

    result = service.reset_password(
        "admin",
        "operator",
        temporary_password="Temporary-Password-123!",
    )

    assert result.success is True
    assert result.username == "operator"
    assert (
        result.temporary_password
        == "Temporary-Password-123!"
    )
    assert result.password_change_required is True

    assert passwords.hashes == [
        "Temporary-Password-123!"
    ]

    assert repository.password_changes == [
        (
            "operator",
            "hash:Temporary-Password-123!",
            True,
        )
    ]


def test_non_admin_cannot_reset_password():
    service, repository, passwords = make_service()

    result = service.reset_password(
        "operator",
        "admin",
        temporary_password="Temporary-Password!",
    )

    assert result.success is False
    assert (
        result.reason
        == "Administrator authorization required"
    )
    assert passwords.hashes == []
    assert repository.password_changes == []


def test_unknown_administrator_cannot_reset_password():
    service, repository, passwords = make_service()

    result = service.reset_password(
        "missing",
        "operator",
        temporary_password="Temporary-Password!",
    )

    assert result.success is False
    assert (
        result.reason
        == "Administrator authorization required"
    )
    assert passwords.hashes == []
    assert repository.password_changes == []


def test_admin_reset_rejects_unknown_target():
    service, repository, passwords = make_service()

    result = service.reset_password(
        "admin",
        "missing",
        temporary_password="Temporary-Password!",
    )

    assert result.success is False
    assert result.reason == "User not found"
    assert passwords.hashes == []
    assert repository.password_changes == []


def test_admin_reset_normalizes_target_username():
    service, repository, _ = make_service()

    result = service.reset_password(
        "ADMIN",
        "  OPERATOR  ",
        temporary_password="Temporary-Password!",
    )

    assert result.success is True
    assert result.username == "operator"


def test_admin_reset_generates_temporary_password():
    service, repository, passwords = make_service()

    result = service.reset_password(
        "admin",
        "operator",
    )

    assert result.success is True
    assert result.username == "operator"
    assert result.password_change_required is True
    assert result.temporary_password
    assert len(result.temporary_password) == (
        service.TEMPORARY_PASSWORD_LENGTH
    )

    assert passwords.hashes == [
        result.temporary_password
    ]


def test_reset_result_contains_no_password_hash():
    service, _, _ = make_service()

    result = service.reset_password(
        "admin",
        "operator",
        temporary_password="Temporary-Password!",
    )

    assert not hasattr(
        result,
        "password_hash",
    )


def test_locked_user_cannot_change_password():
    service, repository, passwords = make_service()

    repository.users["admin"]["failed_login_attempts"] = 5

    result = service.change_password(
        "admin",
        "CurrentPassword!",
        "NewPassword!",
    )

    assert result.success is False
    assert result.reason == "Account locked"
    assert passwords.verifications == []
    assert passwords.hashes == []
    assert repository.password_changes == []
