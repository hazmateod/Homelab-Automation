from himp.services.authentication import (
    AuthenticationService,
)


class FakeRepository:
    def __init__(self):
        self.users = {
            "admin": {
                "username": "admin",
                "password_hash": "correct-hash",
                "active": True,
                "failed_login_attempts": 0,
                "password_change_required": False,
                "role": "admin",
                "display_name": "Administrator",
            }
        }

        self.failures = []
        self.successes = []

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

        class User:
            pass

        result = User()
        result.username = user["username"]
        result.role = user["role"]
        result.display_name = user["display_name"]

        return result

    def record_login_failure(self, username):
        self.users[username][
            "failed_login_attempts"
        ] += 1

        self.failures.append(username)

    def update_login_success(self, username):
        self.users[username][
            "failed_login_attempts"
        ] = 0

        self.successes.append(username)


class FakePasswordService:
    def __init__(self, valid=True):
        self.valid = valid
        self.verifications = []

    def verify(self, password, password_hash):
        self.verifications.append(
            (password, password_hash)
        )
        return self.valid


def make_service(valid=True):
    repository = FakeRepository()

    service = AuthenticationService(
        repository=repository,
        passwords=FakePasswordService(valid),
    )

    return service, repository


def test_correct_password_authenticates():
    service, repository = make_service()

    result = service.authenticate(
        "admin",
        "CorrectPassword!",
    )

    assert result.success is True
    assert result.username == "admin"
    assert result.role == "admin"
    assert result.display_name == "Administrator"
    assert result.password_change_required is False
    assert result.reason is None
    assert repository.successes == ["admin"]


def test_username_is_normalized():
    service, repository = make_service()

    result = service.authenticate(
        "  ADMIN  ",
        "CorrectPassword!",
    )

    assert result.success is True
    assert result.username == "admin"


def test_wrong_password_records_failure():
    service, repository = make_service(
        valid=False
    )

    result = service.authenticate(
        "admin",
        "WrongPassword!",
    )

    assert result.success is False
    assert result.reason == "Invalid credentials"
    assert repository.failures == ["admin"]
    assert (
        repository.users["admin"][
            "failed_login_attempts"
        ]
        == 1
    )


def test_fifth_failed_attempt_locks_account():
    service, repository = make_service(
        valid=False
    )

    for _ in range(5):
        result = service.authenticate(
            "admin",
            "WrongPassword!",
        )

    assert result.success is False
    assert result.reason == "Account locked"
    assert (
        repository.users["admin"][
            "failed_login_attempts"
        ]
        == 5
    )


def test_locked_account_rejects_correct_password():
    service, repository = make_service()

    repository.users["admin"][
        "failed_login_attempts"
    ] = 5

    result = service.authenticate(
        "admin",
        "CorrectPassword!",
    )

    assert result.success is False
    assert result.reason == "Account locked"
    assert repository.successes == []


def test_disabled_account_is_rejected():
    service, repository = make_service()

    repository.users["admin"]["active"] = False

    result = service.authenticate(
        "admin",
        "CorrectPassword!",
    )

    assert result.success is False
    assert result.reason == "Invalid credentials"


def test_unknown_user_still_performs_password_verification():
    service, _ = make_service()

    result = service.authenticate(
        "missing",
        "WrongPassword!",
    )

    assert result.success is False
    assert result.reason == "Invalid credentials"
    assert len(service.passwords.verifications) == 1
    assert (
        service.passwords.verifications[0][0]
        == "WrongPassword!"
    )
    assert (
        service.passwords.verifications[0][1]
        == AuthenticationService.DUMMY_PASSWORD_HASH
    )


def test_unknown_user_does_not_reveal_account_state():
    service, _ = make_service()

    result = service.authenticate(
        "missing",
        "WrongPassword!",
    )

    assert result.success is False
    assert result.reason == "Invalid credentials"


def test_successful_login_resets_failures():
    service, repository = make_service()

    repository.users["admin"][
        "failed_login_attempts"
    ] = 3

    result = service.authenticate(
        "admin",
        "CorrectPassword!",
    )

    assert result.success is True
    assert (
        repository.users["admin"][
            "failed_login_attempts"
        ]
        == 0
    )


def test_password_change_required_is_returned():
    service, repository = make_service()

    repository.users["admin"][
        "password_change_required"
    ] = True

    result = service.authenticate(
        "admin",
        "CorrectPassword!",
    )

    assert result.success is True
    assert result.password_change_required is True


def test_password_hash_is_not_returned():
    service, _ = make_service()

    result = service.authenticate(
        "admin",
        "CorrectPassword!",
    )

    assert not hasattr(
        result,
        "password_hash",
    )


def test_invalid_username_is_rejected():
    service, _ = make_service()

    result = service.authenticate(
        "   ",
        "CorrectPassword!",
    )

    assert result.success is False
    assert result.reason == "Invalid credentials"


def test_non_string_password_is_rejected():
    service, _ = make_service()

    result = service.authenticate(
        "admin",
        None,
    )

    assert result.success is False
    assert result.reason == "Invalid credentials"


def test_successful_authentication_logs_security_event(
    monkeypatch,
):
    import logging

    from himp.lib.security_events import (
        LOGIN_SUCCESS,
    )

    service, _ = make_service()
    records = []

    class CaptureHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    logger = logging.getLogger("himp.security")
    handler = CaptureHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        result = service.authenticate(
            "admin",
            "CorrectPassword!",
        )
    finally:
        logger.removeHandler(handler)

    assert result.success is True
    assert len(records) == 1
    assert records[0].event == LOGIN_SUCCESS
    assert records[0].username == "admin"
    assert records[0].outcome == "success"
    assert "CorrectPassword!" not in records[0].getMessage()


def test_failed_authentication_logs_security_event(
    monkeypatch,
):
    import logging

    from himp.lib.security_events import (
        LOGIN_FAILURE,
    )

    service, _ = make_service(valid=False)
    records = []

    class CaptureHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    logger = logging.getLogger("himp.security")
    handler = CaptureHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        result = service.authenticate(
            "admin",
            "WrongPassword!",
        )
    finally:
        logger.removeHandler(handler)

    assert result.success is False
    assert result.reason == "Invalid credentials"
    assert len(records) == 1
    assert records[0].event == LOGIN_FAILURE
    assert records[0].username == "admin"
    assert records[0].outcome == "failure"
    assert records[0].reason == "Invalid credentials"
    assert "WrongPassword!" not in records[0].getMessage()


def test_locked_account_logs_security_event(
    monkeypatch,
):
    import logging

    from himp.lib.security_events import (
        ACCOUNT_LOCKED,
        LOGIN_FAILURE,
    )

    service, repository = make_service(valid=False)
    records = []

    class CaptureHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    logger = logging.getLogger("himp.security")
    handler = CaptureHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        for _ in range(5):
            result = service.authenticate(
                "admin",
                "WrongPassword!",
            )
    finally:
        logger.removeHandler(handler)

    assert result.success is False
    assert result.reason == "Account locked"

    assert len(records) == 5

    assert [
        record.event
        for record in records
    ] == [
        LOGIN_FAILURE,
        LOGIN_FAILURE,
        LOGIN_FAILURE,
        LOGIN_FAILURE,
        ACCOUNT_LOCKED,
    ]

    assert all(
        record.username == "admin"
        for record in records
    )

    assert all(
        record.outcome == "failure"
        for record in records
    )

    assert records[-1].reason == "Account locked"

    assert all(
        "WrongPassword!" not in record.getMessage()
        for record in records
    )
