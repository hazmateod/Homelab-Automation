"""Fixture coverage for the Technitium health filter contract."""

import pytest

from playbooks.filter_plugins.technitium_health import (
    technitium_dns_result,
    technitium_units,
)


def unit(name, *, canonical=None, enabled=True, active=True, directory="/etc/dns"):
    return {
        "item": name,
        "rc": 0,
        "stdout": "\n".join([
            f"Id={canonical or name}",
            "LoadState=loaded",
            f"ActiveState={'active' if active else 'inactive'}",
            f"UnitFileState={'enabled' if enabled else 'disabled'}",
            f"ExecStart={{ path=/usr/bin/dotnet ; argv[]=/usr/bin/dotnet /opt/technitium/dns/DnsServerApp.dll {directory} ; }}",
            "NRestarts=226000",
            "MainPID=77",
            "DynamicUser=no",
        ]),
    }


@pytest.mark.parametrize("primary", ["dns.service", "technitium.service"])
def test_supported_primary_units(primary):
    other = "dns.service" if primary == "technitium.service" else "technitium.service"
    report = technitium_units([unit(primary), unit(other, enabled=False, active=False)])
    assert report["units"][primary]["active"]
    assert report["units"][primary]["restarts"] == 226000
    assert not report["duplicate_enabled"]


def test_equivalence_requires_distinct_enabled_units_and_matching_arguments():
    primary = unit("dns.service")
    assert technitium_units([primary, unit("technitium.service")])["duplicate_enabled"]
    assert not technitium_units([
        primary, unit("technitium.service", canonical="dns.service")
    ])["duplicate_enabled"]
    assert not technitium_units([
        primary, unit("technitium.service", directory="/etc/other")
    ])["duplicate_enabled"]


def test_permission_denial_and_missing_unit_have_distinct_evidence():
    report = technitium_units([
        {"item": "dns.service", "rc": 1, "stderr": "Access denied"},
        {"item": "technitium.service", "rc": 1, "stdout": "LoadState=not-found"},
    ])
    assert report["errors"] == {"dns.service": "no_permission"}
    assert report["units"] == {}


@pytest.mark.parametrize(("status", "expected"), [
    ("SERVFAIL", "servfail"), ("REFUSED", "refused"), ("NXDOMAIN", "nxdomain"),
    ("NOERROR", "ok"),
])
def test_dns_response_status(status, expected):
    result = {
        "rc": 0,
        "stdout": f";; ->>HEADER<<- opcode: QUERY, status: {status}, id: 1\n"
                  "probe.example. 10 IN A 192.0.2.1",
    }
    assert technitium_dns_result(result, "192.0.2.1") == expected


def test_dns_timeout_missing_tool_and_missing_expected_answer():
    assert technitium_dns_result({"rc": 9, "stdout": "connection timed out"}, "") == "timeout"
    assert technitium_dns_result({"rc": 2}, "") == "unknown"
    assert technitium_dns_result({"skipped": True}, "") == "unknown"
    assert technitium_dns_result({"rc": 0, "stdout": "status: NOERROR,"}, "") == "unexpected_answer"


def test_restart_trend_rejects_replaced_and_stale_hosts():
    import json

    from playbooks.filter_plugins.technitium_health import technitium_restart_trend

    identity = {"host_id": 1, "incarnation": 2}
    binding = {**identity, "ip": "192.0.2.1", "user": "observer"}
    sample = {
        "boot_id": "boot",
        "observed_at": "2026-11-23T01:03:00Z",
        "service_state": {"units": {"dns.service": {"restarts": 226000}}},
    }
    old = {
        **sample,
        "observed_at": "2026-11-23T01:00:00Z",
        "service_state": {"units": {"dns.service": {"restarts": 225997}}},
    }
    previous = json.dumps({"hosts": [{"host_identity": identity, "report": old}]})
    assert technitium_restart_trend(sample, previous, binding, binding["ip"], "observer") == {
        "dns.service": {"delta": 3, "seconds": 180}
    }
    for change in ({"incarnation": 3}, {"host_id": 2}, {"ip": "192.0.2.2"}):
        assert not technitium_restart_trend(
            sample, previous, {**binding, **change}, binding["ip"], "observer"
        )
    for change in ({"observed_at": "2026-11-25T01:00:00Z"}, {"boot_id": "replacement"}):
        assert not technitium_restart_trend(
            {**sample, **change}, previous, binding, binding["ip"], "observer"
        )


@pytest.mark.parametrize(("percent", "severity"), [
    (79, "healthy"), (80, "warning"), (89, "warning"), (90, "critical"),
])
def test_capacity_boundaries_and_retention_evidence(percent, severity):
    from playbooks.filter_plugins.technitium_health import technitium_capacity_report

    report = technitium_capacity_report(
        {"rc": 0, "stdout": f"blocks free usage inodes free used\n5000 300 {percent}% 2000 500 75%"},
        [
            {"item": "/root/backups", "rc": 0, "stdout": "600\t/root/backups"},
            {"item": "/var/log/technitium/dns", "rc": 1, "stdout": "100\tpartial"},
        ],
        {"rc": 0, "stdout": "86400.000\n950400.000"},
        {"exists": True, "isreg": True, "executable": True},
        "1970-04-02T00:00:00Z",
    )
    assert report["root"]["severity"] == severity
    assert report["root"]["available_bytes"] == 307200
    assert report["local_backup_bytes"] == 600
    assert report["query_log_bytes"] is None
    assert report["eligible_logs"] == 1
    assert report["last_successful_retention"] is None
    assert report["pbs_backup"] == "unknown"
    assert report["restore_verification"] == "unknown"
