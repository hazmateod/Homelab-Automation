import pytest

from himp.services.passwords import PasswordService


def test_hash_returns_argon2id_hash():
    service = PasswordService()

    password_hash = service.hash(
        "Correct-Horse-Battery-Staple!"
    )

    assert password_hash.startswith(
        "$argon2id$"
    )


def test_hash_does_not_return_plaintext_password():
    service = PasswordService()

    password = "Correct-Horse-Battery-Staple!"
    password_hash = service.hash(password)

    assert password_hash != password
    assert password not in password_hash


def test_same_password_generates_different_hashes():
    service = PasswordService()

    first = service.hash("SamePassword!")
    second = service.hash("SamePassword!")

    assert first != second


def test_correct_password_verifies():
    service = PasswordService()

    password = "Correct-Horse-Battery-Staple!"
    password_hash = service.hash(password)

    assert service.verify(
        password,
        password_hash,
    ) is True


def test_incorrect_password_does_not_verify():
    service = PasswordService()

    password_hash = service.hash(
        "Correct-Horse-Battery-Staple!"
    )

    assert service.verify(
        "Wrong-Password!",
        password_hash,
    ) is False


def test_malformed_hash_does_not_verify():
    service = PasswordService()

    assert service.verify(
        "SomePassword!",
        "not-a-valid-argon2-hash",
    ) is False


def test_empty_password_is_rejected():
    service = PasswordService()

    with pytest.raises(
        ValueError,
        match="Password cannot be empty",
    ):
        service.hash("")


@pytest.mark.parametrize(
    "password",
    [
        None,
        12345,
        b"password",
    ],
)
def test_non_string_password_is_rejected(password):
    service = PasswordService()

    with pytest.raises(
        TypeError,
        match="Password must be a string",
    ):
        service.hash(password)
