import pytest

from himp.services.password_policy import (
    PasswordPolicyService,
)


def test_valid_password_is_accepted():
    service = PasswordPolicyService()

    result = service.validate(
        "Correct-Horse-Battery-Staple!"
    )

    assert result.valid is True
    assert result.reason is None


def test_passphrase_with_spaces_is_accepted():
    service = PasswordPolicyService()

    result = service.validate(
        "correct horse battery staple"
    )

    assert result.valid is True


def test_password_at_minimum_length_is_accepted():
    service = PasswordPolicyService()

    result = service.validate(
        "a" * service.MIN_LENGTH
    )

    assert result.valid is True


def test_password_below_minimum_length_is_rejected():
    service = PasswordPolicyService()

    result = service.validate(
        "a" * (service.MIN_LENGTH - 1)
    )

    assert result.valid is False
    assert result.reason == (
        "Password must be at least 12 characters"
    )


def test_password_at_maximum_length_is_accepted():
    service = PasswordPolicyService()

    result = service.validate(
        "a" * service.MAX_LENGTH
    )

    assert result.valid is True


def test_password_above_maximum_length_is_rejected():
    service = PasswordPolicyService()

    result = service.validate(
        "a" * (service.MAX_LENGTH + 1)
    )

    assert result.valid is False
    assert result.reason == (
        "Password cannot exceed 128 characters"
    )


@pytest.mark.parametrize(
    "password",
    [
        "",
        " " * 12,
        "\t" * 12,
        "\n" * 12,
    ],
)
def test_blank_password_is_rejected(password):
    service = PasswordPolicyService()

    result = service.validate(password)

    assert result.valid is False
    assert result.reason == "Password cannot be empty"


@pytest.mark.parametrize(
    "password",
    [
        None,
        12345,
        b"password",
    ],
)
def test_non_string_password_is_rejected(password):
    service = PasswordPolicyService()

    result = service.validate(password)

    assert result.valid is False
    assert result.reason == "Password must be a string"
