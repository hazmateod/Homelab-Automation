"""Tests for durable host automation exclusions."""

import sqlite3

import pytest

from himp.database.host_automation_policies import (
    HostAutomationPolicyRepository,
)


class TestDatabase:
    """Isolated SQLite implementation of the repository contract."""

    __test__ = False

    def __init__(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row

    def execute(self, sql, parameters=()):
        return self.connection.execute(sql, parameters)

    def query(self, sql, parameters=()):
        return self.connection.execute(sql, parameters).fetchall()

    def transaction(self):
        from contextlib import contextmanager

        @contextmanager
        def transaction_context():
            try:
                yield self.connection
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise

        return transaction_context()


@pytest.fixture
def repository():
    database = TestDatabase()
    repo = HostAutomationPolicyRepository(database=database)
    yield repo
    database.connection.close()


def test_unknown_host_defaults_to_enabled(repository):
    policy = repository.get("example.server.arpa")

    assert policy["enabled"] is True
    assert policy["reason"] == ""
    assert policy["changed_by"] is None


def test_disable_host_with_reason(repository):
    policy = repository.set_policy(
        "example.server.arpa",
        False,
        "Temporarily powered off",
        "admin",
    )

    assert policy["enabled"] is False
    assert policy["reason"] == "Temporarily powered off"
    assert policy["changed_by"] == "admin"

    assert repository.disabled_hosts() == {
        "example.server.arpa"
    }


def test_reenable_host(repository):
    repository.set_policy(
        "example.server.arpa",
        False,
        "Maintenance",
        "admin",
    )

    policy = repository.set_policy(
        "example.server.arpa",
        True,
        "Maintenance complete",
        "admin",
    )

    assert policy["enabled"] is True
    assert repository.disabled_hosts() == set()


def test_disabling_requires_reason(repository):
    with pytest.raises(ValueError, match="reason"):
        repository.set_policy(
            "example.server.arpa",
            False,
            "",
            "admin",
        )


@pytest.mark.parametrize(
    "hostname,enabled,reason,actor",
    [
        ("", False, "Maintenance", "admin"),
        ("example", False, "Maintenance", ""),
        ("example", "false", "Maintenance", "admin"),
        (None, False, "Maintenance", "admin"),
        ("example", False, None, "admin"),
    ],
)
def test_invalid_policy_input(
    repository,
    hostname,
    enabled,
    reason,
    actor,
):
    with pytest.raises(ValueError):
        repository.set_policy(
            hostname,
            enabled,
            reason,
            actor,
        )


def test_audit_history(repository):
    repository.set_policy(
        "example.server.arpa",
        False,
        "Offline",
        "admin",
    )

    repository.set_policy(
        "example.server.arpa",
        True,
        "Online",
        "admin",
    )

    history = repository.history("example.server.arpa")

    assert len(history) == 2

    assert history[0]["old_enabled"] is False
    assert history[0]["new_enabled"] is True

    assert history[1]["old_enabled"] is True
    assert history[1]["new_enabled"] is False


def test_failed_audit_insert_rolls_back_policy(repository):
    repository.database.execute(
        """
        CREATE TRIGGER reject_policy_audit
        BEFORE INSERT ON host_automation_policy_audit
        BEGIN
            SELECT RAISE(ABORT, 'audit rejected');
        END
        """
    )
    repository.database.connection.commit()

    with pytest.raises(sqlite3.IntegrityError):
        repository.set_policy(
            "example.server.arpa",
            False,
            "Offline",
            "admin",
        )

    assert repository.get(
        "example.server.arpa"
    )["enabled"] is True

    assert repository.disabled_hosts() == set()


def test_history_limit_validation(repository):
    for invalid in (0, -1, True, "10"):
        with pytest.raises(ValueError):
            repository.history(
                "example.server.arpa",
                limit=invalid,
            )
