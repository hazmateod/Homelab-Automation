import hashlib
from datetime import datetime, timedelta

from himp.services.sessions import SessionService


class FakeRepository:
    def __init__(self):
        self.sessions = {}
        self.created = []
        self.touched = []
        self.revoked = []
        self.revoked_all = []
        self.cleaned = []

    def create(
        self,
        token_hash,
        username,
        created_at,
        expires_at,
    ):
        session = {
            "token_hash": token_hash,
            "username": username,
            "created_at": created_at,
            "expires_at": expires_at,
            "revoked_at": None,
            "last_seen_at": created_at,
        }

        self.sessions[token_hash] = session
        self.created.append(session)

        return session

    def active(self, token_hash, now):
        session = self.sessions.get(token_hash)

        if session is None:
            return None

        if session["revoked_at"] is not None:
            return None

        if session["expires_at"] <= now:
            return None

        return session

    def touch(self, token_hash, now):
        session = self.sessions.get(token_hash)

        if session is not None:
            session["last_seen_at"] = now

        self.touched.append(
            (token_hash, now)
        )

    def revoke(self, token_hash, now):
        session = self.sessions.get(token_hash)

        if session is not None:
            session["revoked_at"] = now

        self.revoked.append(
            (token_hash, now)
        )

    def revoke_all(self, username, now):
        for session in self.sessions.values():
            if (
                session["username"] == username
                and session["revoked_at"] is None
            ):
                session["revoked_at"] = now

        self.revoked_all.append(
            (username, now)
        )

    def delete_expired(self, now):
        self.cleaned.append(now)
        return 3


def make_service():
    repository = FakeRepository()
    service = SessionService(
        repository=repository
    )
    return service, repository


def test_create_session_returns_plaintext_token_once():
    service, repository = make_service()

    now = datetime(2026, 1, 1, 12, 0)

    result = service.create_session(
        " Admin ",
        now=now,
    )

    assert result.success is True
    assert result.token is not None
    assert result.username == "admin"
    assert result.created_at == now
    assert result.expires_at == (
        now + timedelta(hours=8)
    )
    assert result.last_seen_at == now
    assert len(result.token) > 20

    assert len(repository.created) == 1
    assert repository.created[0]["username"] == "admin"


def test_plaintext_token_is_never_persisted():
    service, repository = make_service()

    result = service.create_session(
        "admin",
        now=datetime(2026, 1, 1, 12, 0),
    )

    stored = repository.created[0]["token_hash"]

    assert stored != result.token
    assert stored == hashlib.sha256(
        result.token.encode("utf-8")
    ).hexdigest()


def test_each_session_gets_a_unique_token():
    service, repository = make_service()

    first = service.create_session("admin")
    second = service.create_session("admin")

    assert first.token != second.token
    assert (
        repository.created[0]["token_hash"]
        != repository.created[1]["token_hash"]
    )


def test_authenticate_session_succeeds():
    service, repository = make_service()

    created = datetime(2026, 1, 1, 12, 0)

    created_result = service.create_session(
        "admin",
        now=created,
    )

    now = created + timedelta(minutes=15)

    result = service.authenticate_session(
        created_result.token,
        now=now,
    )

    assert result.success is True
    assert result.username == "admin"
    assert result.created_at == created
    assert result.expires_at == (
        created + timedelta(hours=8)
    )
    assert result.last_seen_at == now
    assert len(repository.touched) == 1


def test_authentication_hashes_token_before_lookup():
    service, repository = make_service()

    result = service.create_session(
        "admin",
        now=datetime(2026, 1, 1, 12, 0),
    )

    stored_hash = repository.created[0]["token_hash"]

    assert stored_hash == (
        service._hash_token(result.token)
    )


def test_unknown_token_is_rejected():
    service, repository = make_service()

    result = service.authenticate_session(
        "unknown-token"
    )

    assert result.success is False
    assert result.token is None
    assert result.username is None
    assert result.reason == "Invalid session"
    assert repository.touched == []


def test_empty_token_is_rejected():
    service, repository = make_service()

    result = service.authenticate_session("")

    assert result.success is False
    assert result.reason == "Invalid session"
    assert repository.touched == []


def test_non_string_token_is_rejected():
    service, repository = make_service()

    result = service.authenticate_session(None)

    assert result.success is False
    assert result.reason == "Invalid session"
    assert repository.touched == []


def test_expired_session_is_rejected():
    service, repository = make_service()

    created = datetime(2026, 1, 1, 12, 0)

    created_result = service.create_session(
        "admin",
        now=created,
    )

    result = service.authenticate_session(
        created_result.token,
        now=created + timedelta(hours=8),
    )

    assert result.success is False
    assert result.reason == "Invalid session"
    assert repository.touched == []


def test_revoke_session():
    service, repository = make_service()

    created = datetime(2026, 1, 1, 12, 0)

    created_result = service.create_session(
        "admin",
        now=created,
    )

    revoked = created + timedelta(minutes=5)

    assert service.revoke_session(
        created_result.token,
        now=revoked,
    ) is True

    result = service.authenticate_session(
        created_result.token,
        now=revoked,
    )

    assert result.success is False
    assert result.reason == "Invalid session"


def test_revoke_all_sessions():
    service, repository = make_service()

    now = datetime(2026, 1, 1, 12, 0)

    first = service.create_session(
        "admin",
        now=now,
    )

    second = service.create_session(
        "admin",
        now=now,
    )

    service.create_session(
        "operator",
        now=now,
    )

    revoked = now + timedelta(minutes=5)

    assert service.revoke_all_sessions(
        " ADMIN ",
        now=revoked,
    ) is True

    assert service.authenticate_session(
        first.token,
        now=revoked,
    ).success is False

    assert service.authenticate_session(
        second.token,
        now=revoked,
    ).success is False


def test_cleanup_returns_deleted_count():
    service, repository = make_service()

    now = datetime(2026, 1, 1, 12, 0)

    result = service.cleanup(now=now)

    assert result == 3
    assert repository.cleaned == [now]


def test_invalid_username_is_rejected():
    service, repository = make_service()

    result = service.create_session(
        "   ",
        now=datetime(2026, 1, 1, 12, 0),
    )

    assert result.success is False
    assert result.reason == "Invalid username"
    assert repository.created == []


def test_non_string_username_is_rejected():
    service, repository = make_service()

    result = service.create_session(
        None,
        now=datetime(2026, 1, 1, 12, 0),
    )

    assert result.success is False
    assert result.reason == "Invalid username"
    assert repository.created == []


def test_invalid_revoke_token_is_rejected():
    service, repository = make_service()

    assert service.revoke_session(
        None
    ) is False

    assert service.revoke_session(
        ""
    ) is False

    assert repository.revoked == []


def test_invalid_revoke_all_username_is_rejected():
    service, repository = make_service()

    assert service.revoke_all_sessions(
        None
    ) is False

    assert service.revoke_all_sessions(
        "   "
    ) is False

    assert repository.revoked_all == []
