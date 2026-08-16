import sqlite3
from datetime import datetime, timedelta

import pytest


def adapt_datetime(value):
    return value.isoformat(" ")


def convert_timestamp(value):
    return datetime.fromisoformat(
        value.decode()
    )


sqlite3.register_adapter(
    datetime,
    adapt_datetime,
)

sqlite3.register_converter(
    "TIMESTAMP",
    convert_timestamp,
)

from himp.database.sessions import SessionRepository


class TemporaryDatabase:
    def __init__(self):
        self.connection = sqlite3.connect(
            ":memory:",
            detect_types=sqlite3.PARSE_DECLTYPES,
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


    def execute_affected(
        self,
        sql,
        parameters=(),
    ):
        cursor = self.execute(
            sql,
            parameters,
        )

        return cursor.rowcount

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
        SessionRepository
    )

    repository.database = TemporaryDatabase()
    repository._ensure_table()

    return repository


def make_times():
    created = datetime(2026, 1, 1, 12, 0, 0)
    expires = created + timedelta(hours=8)

    return created, expires


def token_hash(character="a"):
    return character * 64


def test_create_and_get_session():
    repository = make_repository()
    created, expires = make_times()

    session = repository.create(
        token_hash(),
        "Admin",
        created,
        expires,
    )

    assert session is not None
    assert session["token_hash"] == token_hash()
    assert session["username"] == "admin"
    assert session["created_at"] == created
    assert session["expires_at"] == expires
    assert session["revoked_at"] is None
    assert session["last_seen_at"] == created


def test_plaintext_token_is_not_stored():
    repository = make_repository()
    created, expires = make_times()

    plaintext_token = "super-secret-session-token"

    repository.create(
        token_hash(),
        "admin",
        created,
        expires,
    )

    rows = repository.database.query(
        "SELECT * FROM sessions"
    )

    assert plaintext_token not in str(rows)


def test_active_returns_unexpired_unrevoked_session():
    repository = make_repository()
    created, expires = make_times()

    repository.create(
        token_hash(),
        "admin",
        created,
        expires,
    )

    active = repository.active(
        token_hash(),
        created + timedelta(hours=1),
    )

    assert active is not None
    assert active["username"] == "admin"


def test_expired_session_is_not_active():
    repository = make_repository()
    created, expires = make_times()

    repository.create(
        token_hash(),
        "admin",
        created,
        expires,
    )

    assert repository.active(
        token_hash(),
        expires,
    ) is None


def test_revoke_makes_session_inactive():
    repository = make_repository()
    created, expires = make_times()

    repository.create(
        token_hash(),
        "admin",
        created,
        expires,
    )

    repository.revoke(
        token_hash(),
        created + timedelta(minutes=5),
    )

    assert repository.active(
        token_hash(),
        created + timedelta(minutes=10),
    ) is None


def test_touch_updates_last_seen():
    repository = make_repository()
    created, expires = make_times()

    repository.create(
        token_hash(),
        "admin",
        created,
        expires,
    )

    touched = created + timedelta(minutes=15)

    repository.touch(
        token_hash(),
        touched,
    )

    session = repository.get(token_hash())

    assert session["last_seen_at"] == touched


def test_touch_does_not_update_expired_session():
    repository = make_repository()
    created, expires = make_times()

    repository.create(
        token_hash(),
        "admin",
        created,
        expires,
    )

    repository.touch(
        token_hash(),
        expires,
    )

    session = repository.get(token_hash())

    assert session["last_seen_at"] == created


def test_revoke_all_revokes_user_sessions():
    repository = make_repository()
    created, expires = make_times()

    repository.create(
        token_hash("a"),
        "admin",
        created,
        expires,
    )

    repository.create(
        token_hash("b"),
        "admin",
        created,
        expires,
    )

    repository.create(
        token_hash("c"),
        "operator",
        created,
        expires,
    )

    repository.revoke_all(
        "ADMIN",
        created + timedelta(minutes=1),
    )

    assert repository.active(
        token_hash("a"),
        created + timedelta(minutes=2),
    ) is None

    assert repository.active(
        token_hash("b"),
        created + timedelta(minutes=2),
    ) is None

    assert repository.active(
        token_hash("c"),
        created + timedelta(minutes=2),
    ) is not None


def test_delete_expired_removes_expired_sessions():
    repository = make_repository()
    created, expires = make_times()

    repository.create(
        token_hash(),
        "admin",
        created,
        expires,
    )

    deleted = repository.delete_expired(
        expires,
    )

    assert deleted == 1
    assert repository.get(token_hash()) is None


def test_delete_expired_removes_revoked_sessions():
    repository = make_repository()
    created, expires = make_times()

    repository.create(
        token_hash(),
        "admin",
        created,
        expires,
    )

    repository.revoke(
        token_hash(),
        created + timedelta(minutes=1),
    )

    deleted = repository.delete_expired(
        created + timedelta(minutes=2),
    )

    assert deleted == 1
    assert repository.get(token_hash()) is None


def test_duplicate_token_hash_is_rejected():
    repository = make_repository()
    created, expires = make_times()

    repository.create(
        token_hash(),
        "admin",
        created,
        expires,
    )

    with pytest.raises(sqlite3.IntegrityError):
        repository.create(
            token_hash(),
            "operator",
            created,
            expires,
        )


def test_invalid_token_hash_is_rejected():
    repository = make_repository()
    created, expires = make_times()

    with pytest.raises(ValueError):
        repository.create(
            "short",
            "admin",
            created,
            expires,
        )


def test_expiration_must_be_after_creation():
    repository = make_repository()
    created, _ = make_times()

    with pytest.raises(
        ValueError,
        match="Session expiration must be after creation",
    ):
        repository.create(
            token_hash(),
            "admin",
            created,
            created,
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
    created, expires = make_times()

    expected = (
        TypeError
        if not isinstance(username, str)
        else ValueError
    )

    with pytest.raises(expected):
        repository.create(
            token_hash(),
            username,
            created,
            expires,
        )
