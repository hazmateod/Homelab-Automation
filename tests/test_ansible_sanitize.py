"""Phase 17.1 Ansible event sanitization regression tests."""

import json

import pytest

from himp.lib.ansible_sanitize import (
    sanitize_event,
    sanitize_string,
)


def test_sensitive_dictionary_fields_are_redacted():
    result = sanitize_event({
        "password": "synthetic-password",
        "api_key": "synthetic-api-key",
        "nested": {
            "access_token": "synthetic-token",
        },
    })

    assert result["password"] == "[REDACTED]"
    assert result["api_key"] == "[REDACTED]"
    assert result["nested"]["access_token"] == "[REDACTED]"


def test_credentials_inside_error_message_are_redacted():
    message = (
        'password="synthetic-password" '
        'token=synthetic-token '
        'api_key=synthetic-key'
    )

    result = sanitize_string(message)

    assert "synthetic-password" not in result
    assert "synthetic-token" not in result
    assert "synthetic-key" not in result
    assert result.count("[REDACTED]") == 3


def test_url_credentials_are_redacted():
    result = sanitize_string(
        "Connection failed: "
        "https://synthetic-user:synthetic-password@example.test/"
    )

    assert "synthetic-user" not in result
    assert "synthetic-password" not in result
    assert "https://[REDACTED]@" in result


@pytest.mark.parametrize(
    "authorization",
    [
        "Bearer synthetic-bearer-token",
        "Basic c3ludGhldGljOnBhc3N3b3Jk",
    ],
)
def test_authorization_schemes_are_redacted(authorization):
    result = sanitize_string(authorization)

    assert "synthetic-bearer-token" not in result
    assert "c3ludGhldGlj" not in result
    assert "[REDACTED]" in result


def test_authorization_headers_are_redacted():
    result = sanitize_string(
        "Authorization: synthetic-header-secret"
    )

    assert "synthetic-header-secret" not in result


def test_private_key_blocks_are_redacted():
    private_key = (
        "-----BEGIN PRIVATE KEY-----\n"
        "synthetic-private-key-material\n"
        "-----END PRIVATE KEY-----"
    )

    result = sanitize_string(private_key)

    assert "synthetic-private-key-material" not in result
    assert "[REDACTED PRIVATE KEY]" in result


def test_nested_lists_are_sanitized():
    result = sanitize_event({
        "details": [
            {"password": "synthetic-password"},
            ["token=synthetic-token"],
        ],
    })

    serialized = json.dumps(result)

    assert "synthetic-password" not in serialized
    assert "synthetic-token" not in serialized


def test_diagnostic_output_is_bounded():
    result = sanitize_string("A" * 5000)

    assert len(result) < 2100
    assert result.endswith("...[TRUNCATED]")


def test_collection_size_is_bounded():
    result = sanitize_event({
        "items": list(range(150)),
    })

    assert len(result["items"]) == 101
    assert result["items"][-1] == "[TRUNCATED]"


def test_recursion_depth_is_bounded():
    value = "safe"

    for _ in range(20):
        value = {"nested": value}

    result = sanitize_event(value)

    for _ in range(20):
        if not isinstance(result, dict):
            break
        result = result["nested"]

    assert result == "[MAXIMUM DEPTH EXCEEDED]"


def test_unknown_objects_are_not_serialized():
    class SecretObject:
        def __repr__(self):
            return "synthetic-secret-object"

    result = sanitize_event({
        "details": SecretObject(),
    })

    assert result["details"] == "[UNSUPPORTED VALUE]"
    assert "synthetic-secret-object" not in json.dumps(result)


def test_sensitive_values_never_appear_in_serialized_event():
    payload = {
        "event": "failed",
        "host": "synthetic-host",
        "error": (
            "Authentication failed for "
            "user=synthetic-user password=synthetic-password"
        ),
        "details": {
            "password": "another-synthetic-password",
            "message": "Bearer synthetic-secret-token",
        },
    }

    serialized = json.dumps(sanitize_event(payload))

    for secret in (
        "synthetic-user",
        "synthetic-password",
        "another-synthetic-password",
        "synthetic-secret-token",
    ):
        assert secret not in serialized
