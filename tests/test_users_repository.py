import sqlite3

import pytest

from himp.database.users import UserRepository


class TemporaryDatabase:
    def __init__(self):
        self.connection = sqlite3.connect(
            ":memory:"
        )
        self.connection.row_factory = sqlite3.Row

    def execute(
        self,
        sql,
        parameters=(),
    ):
        cursor = self.connection.cursor()
        cursor.execute(sql, parameters)
        self.connection.commit()
        return cursor

    def query(
        self,
        sql,
        parameters=(),
    ):
        cursor = self.connection.cursor()
        cursor.execute(sql, parameters)
        return cursor.fetchall()


def make_repository():
    repository = object.__new__(
        UserRepository
    )

    repository.database = TemporaryDatabase()
    repository._ensure_table()

    return repository


def test_create_and_get_user():
    repository = make_repository()

    user = repository.create(
        "admin",
        "$argon2id$test",
        "admin",
        "Administrator",
    )

    assert user.username == "admin"
    assert user.role == "admin"
    assert user.active is True
    assert user.display_name == "Administrator"
    assert user.failed_login_attempts == 0
    assert user.password_change_required is False
    assert user.created_at is not None
    assert user.updated_at is not None


def test_duplicate_username_is_rejected():
    repository = make_repository()

    repository.create(
        "admin",
        "$argon2id$test",
        "admin",
    )

    with pytest.raises(
        sqlite3.IntegrityError
    ):
        repository.create(
            "admin",
            "$argon2id$test2",
            "admin",
        )


@pytest.mark.parametrize(
    "role",
    [
        "invalid",
        "administrator",
        "",
        None,
    ],
)
def test_invalid_role_is_rejected(role):
    repository = make_repository()

    with pytest.raises(ValueError):
        repository.create(
            "test",
            "$argon2id$test",
            role,
        )


def test_failed_login_attempts_increment():
    repository = make_repository()

    repository.create(
        "admin",
        "$argon2id$test",
        "admin",
    )

    repository.record_login_failure("admin")
    repository.record_login_failure("admin")

    user = repository.get("admin")

    assert user.failed_login_attempts == 2


def test_successful_login_resets_failures_and_records_time():
    repository = make_repository()

    repository.create(
        "admin",
        "$argon2id$test",
        "admin",
    )

    repository.record_login_failure("admin")
    repository.record_login_failure("admin")

    repository.update_login_success("admin")

    user = repository.get("admin")

    assert user.failed_login_attempts == 0
    assert user.last_login_at is not None


def test_disabled_user_is_persisted():
    repository = make_repository()

    repository.create(
        "admin",
        "$argon2id$test",
        "admin",
    )

    repository.set_active(
        "admin",
        False,
    )

    user = repository.get("admin")

    assert user.active is False


def test_password_change_required_is_persisted():
    repository = make_repository()

    repository.create(
        "admin",
        "$argon2id$test",
        "admin",
    )

    repository.set_password_change_required(
        "admin",
        True,
    )

    user = repository.get("admin")

    assert user.password_change_required is True


def test_missing_user_returns_none():
    repository = make_repository()

    assert repository.get("missing") is None


def test_empty_username_is_rejected():
    repository = make_repository()

    with pytest.raises(
        ValueError,
        match="Username cannot be empty",
    ):
        repository.get("")


def test_password_hash_must_be_non_empty_string():
    repository = make_repository()

    with pytest.raises(
        TypeError,
        match="Password hash must be a string",
    ):
        repository.create(
            "admin",
            None,
            "admin",
        )

    with pytest.raises(
        ValueError,
        match="Password hash cannot be empty",
    ):
        repository.create(
            "admin",
            "",
            "admin",
        )


def test_username_is_normalized():
    repository = make_repository()

    repository.create(
        "  Admin  ",
        "$argon2id$test",
        "admin",
    )

    assert repository.get("ADMIN").username == "admin"

    with pytest.raises(sqlite3.IntegrityError):
        repository.create(
            "admin",
            "$argon2id$test2",
            "admin",
        )


@pytest.mark.parametrize(
    "username",
    [
        "",
        "   ",
        None,
        12345,
    ],
)
def test_invalid_username_is_rejected(username):
    repository = make_repository()

    expected = (
        TypeError
        if not isinstance(username, str)
        else ValueError
    )

    with pytest.raises(expected):
        repository.create(
            username,
            "$argon2id$test",
            "admin",
        )


def test_set_password_replaces_hash_and_clears_login_failures():
    repository = make_repository()

    repository.create(
        username="admin",
        password_hash="old-hash",
        role="admin",
        display_name="Administrator",
        password_change_required=True,
    )

    repository.record_login_failure("admin")
    repository.record_login_failure("admin")

    repository.set_password(
        "admin",
        "new-hash",
    )

    credentials = repository.credentials("admin")

    assert credentials is not None
    assert credentials["password_hash"] == "new-hash"
    assert credentials["failed_login_attempts"] == 0
    assert credentials["password_change_required"] is False


def test_set_password_can_require_password_change():
    repository = make_repository()

    repository.create(
        username="admin",
        password_hash="old-hash",
        role="admin",
        display_name="Administrator",
    )

    repository.set_password(
        "admin",
        "temporary-hash",
        password_change_required=True,
    )

    credentials = repository.credentials("admin")

    assert credentials is not None
    assert credentials["password_hash"] == "temporary-hash"
    assert credentials["password_change_required"] is True
    assert credentials["failed_login_attempts"] == 0


def test_set_password_rejects_non_string_hash():
    repository = make_repository()

    repository.create(
        username="admin",
        password_hash="old-hash",
        role="admin",
        display_name="Administrator",
    )

    with pytest.raises(
        TypeError,
        match="Password hash must be a string",
    ):
        repository.set_password(
            "admin",
            None,
        )


def test_set_password_rejects_empty_hash():
    repository = make_repository()

    repository.create(
        username="admin",
        password_hash="old-hash",
        role="admin",
        display_name="Administrator",
    )

    with pytest.raises(
        ValueError,
        match="Password hash cannot be empty",
    ):
        repository.set_password(
            "admin",
            "",
        )


def test_set_password_rejects_non_boolean_password_change_state():
    repository = make_repository()

    repository.create(
        username="admin",
        password_hash="old-hash",
        role="admin",
        display_name="Administrator",
    )

    with pytest.raises(
        TypeError,
        match="Password change required must be a boolean",
    ):
        repository.set_password(
            "admin",
            "new-hash",
            password_change_required="yes",
        )
