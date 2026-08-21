import subprocess

import pytest

from himp.config import config
from himp.services.inventory import InventoryService


class FakeRepository:
    def __init__(self, existing=None):
        self.existing = existing
        self.saved = []

    def find_host(self, hostname, include_inactive=False):
        if self.existing is None:
            return None

        if hostname == self.existing["hostname"]:
            return self.existing

        return None

    def save_host(self, host):
        self.saved.append(host)
        self.existing = {
            "hostname": host["hostname"],
            "group_name": host["group"],
            "ip": host["ip"],
            "ansible_user": host["user"],
            "become": bool(host["become"]),
        }


class FakeWriter:
    def __init__(self):
        self.added = []
        self.updated = []
        self.removed = []

    def add_host(self, **kwargs):
        self.added.append(kwargs)
        return {
            "hostname": kwargs["hostname"],
            "group": kwargs["group"],
            "ip": kwargs["ip"],
            "user": kwargs["user"],
            "become": kwargs["become"],
        }

    def update_host(self, **kwargs):
        self.updated.append(kwargs)
        return {
            "hostname": kwargs["hostname"],
            "group": kwargs["group"],
            "ip": kwargs["ip"],
            "user": kwargs["user"],
            "become": kwargs["become"],
        }

    def remove_host(self, **kwargs):
        self.removed.append(kwargs)
        return None


def make_service(existing=None):
    service = InventoryService.__new__(InventoryService)
    service.repository = FakeRepository(existing)
    service.writer = FakeWriter()
    return service


def test_validate_inventory_host_accepts_matching_inventory_and_ping(
    monkeypatch,
):
    service = make_service()

    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)

        if command[0] == "ansible-inventory":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout='{"ansible_host": "10.10.37.57"}',
                stderr="",
            )

        return subprocess.CompletedProcess(
            command,
            0,
            stdout="himpdb01.server.arpa | SUCCESS => {\"ping\": \"pong\"}",
            stderr="",
        )

    monkeypatch.setattr(
        "himp.services.inventory.subprocess.run",
        fake_run,
    )

    result = service._validate_inventory_host(
        "himpdb01.server.arpa",
        "10.10.37.57",
    )

    assert result["ansible_host"] == "10.10.37.57"

    assert calls[0] == [
        "ansible-inventory",
        "-i",
        config.inventory,
        "--host",
        "himpdb01.server.arpa",
    ]

    assert "--json" not in calls[0]

    assert calls[1][0] == "ansible"
    assert calls[1][3] == "himpdb01.server.arpa"


def test_validate_inventory_host_rejects_unresolved_host(
    monkeypatch,
):
    service = make_service()

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            1,
            stdout="",
            stderr="Could not match supplied host pattern",
        )

    monkeypatch.setattr(
        "himp.services.inventory.subprocess.run",
        fake_run,
    )

    with pytest.raises(
        ValueError,
        match="Ansible inventory validation failed",
    ):
        service._validate_inventory_host(
            "himpdb01.server.arpa",
            "10.10.37.57",
        )


def test_validate_inventory_host_rejects_wrong_ip(
    monkeypatch,
):
    service = make_service()

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"ansible_host": "10.10.37.99"}',
            stderr="",
        )

    monkeypatch.setattr(
        "himp.services.inventory.subprocess.run",
        fake_run,
    )

    with pytest.raises(
        ValueError,
        match="Ansible inventory IP mismatch",
    ):
        service._validate_inventory_host(
            "himpdb01.server.arpa",
            "10.10.37.57",
        )


def test_validate_inventory_host_rejects_failed_ping(
    monkeypatch,
):
    service = make_service()

    def fake_run(command, **kwargs):
        if command[0] == "ansible-inventory":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout='{"ansible_host": "10.10.37.57"}',
                stderr="",
            )

        return subprocess.CompletedProcess(
            command,
            1,
            stdout="",
            stderr="UNREACHABLE",
        )

    monkeypatch.setattr(
        "himp.services.inventory.subprocess.run",
        fake_run,
    )

    with pytest.raises(
        ValueError,
        match="Ansible SSH validation failed",
    ):
        service._validate_inventory_host(
            "himpdb01.server.arpa",
            "10.10.37.57",
        )


def test_add_host_rolls_back_inventory_when_validation_fails(
    monkeypatch,
):
    service = make_service()

    def fail_validation(*args, **kwargs):
        raise ValueError("validation failed")

    monkeypatch.setattr(
        service,
        "_validate_inventory_host",
        fail_validation,
    )

    with pytest.raises(
        ValueError,
        match="validation failed",
    ):
        service.add_host(
            hostname="newhost.server.arpa",
            group="infrastructure",
            ip="10.10.37.99",
            user="root",
        )

    assert service.writer.removed == [
        {"hostname": "newhost.server.arpa"}
    ]
    assert service.repository.saved == []


def test_add_host_saves_cmdb_only_after_validation(
    monkeypatch,
):
    service = make_service()

    monkeypatch.setattr(
        service,
        "_validate_inventory_host",
        lambda **kwargs: {
            "ansible_host": kwargs["expected_ip"]
        },
    )

    result = service.add_host(
        hostname="newhost.server.arpa",
        group="infrastructure",
        ip="10.10.37.99",
        user="root",
    )

    assert result["hostname"] == "newhost.server.arpa"
    assert len(service.repository.saved) == 1
    assert service.writer.removed == []


def test_update_host_restores_previous_inventory_when_validation_fails(
    monkeypatch,
):
    existing = {
        "hostname": "himpdb01.server.arpa",
        "group_name": "infrastructure",
        "ip": "10.10.37.57",
        "ansible_user": "root",
        "become": 0,
    }

    service = make_service(existing)

    def fail_validation(*args, **kwargs):
        raise ValueError("validation failed")

    monkeypatch.setattr(
        service,
        "_validate_inventory_host",
        fail_validation,
    )

    with pytest.raises(
        ValueError,
        match="validation failed",
    ):
        service.update_host(
            hostname="himpdb01.server.arpa",
            group="infrastructure",
            ip="10.10.37.99",
            user="root",
        )

    assert service.writer.updated == [
        {
            "hostname": "himpdb01.server.arpa",
            "group": "infrastructure",
            "ip": "10.10.37.99",
            "user": "root",
            "become": False,
        },
        {
            "hostname": "himpdb01.server.arpa",
            "group": "infrastructure",
            "ip": "10.10.37.57",
            "user": "root",
            "become": False,
        },
    ]
    assert service.repository.saved == []


def test_update_host_saves_cmdb_only_after_validation(
    monkeypatch,
):
    existing = {
        "hostname": "himpdb01.server.arpa",
        "group_name": "infrastructure",
        "ip": "10.10.37.57",
        "ansible_user": "root",
        "become": 0,
    }

    service = make_service(existing)

    monkeypatch.setattr(
        service,
        "_validate_inventory_host",
        lambda **kwargs: {
            "ansible_host": kwargs["expected_ip"]
        },
    )

    result = service.update_host(
        hostname="himpdb01.server.arpa",
        group="infrastructure",
        ip="10.10.37.99",
        user="root",
    )

    assert result["hostname"] == "himpdb01.server.arpa"
    assert len(service.repository.saved) == 1
    assert service.writer.removed == []
    assert len(service.writer.updated) == 1
