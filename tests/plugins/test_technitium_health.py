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
    assert technitium_dns_result(result, "probe.example", "192.0.2.1") == expected


@pytest.mark.parametrize(("result", "outcome"), [
    ({"rc": 9, "stdout": "connection timed out"}, "timeout"),
    ({"rc": 124}, "timeout"),
    ({"rc": 2}, "unknown"),
    ({"skipped": True}, "unknown"),
    ({"rc": 0, "stdout": "status: NOERROR,"}, "unknown"),
    ({"rc": 0, "stdout": ";; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 1"}, "unexpected_answer"),
])
def test_dns_timeout_missing_tool_and_missing_expected_answer(result, outcome):
    assert technitium_dns_result(result, "probe.example", "192.0.2.1") == outcome


@pytest.mark.parametrize(("flags", "record", "outcome"), [
    ("qr rd ra", "other.example. 10 IN A 192.0.2.1", "unexpected_answer"),
    ("qr rd ra", "probe.example. 10 IN A 192.0.2.2", "unexpected_answer"),
    ("qr tc rd ra", "probe.example. 10 IN A 192.0.2.1", "truncated"),
    ("qr rd ra", "PROBE.example. 10 IN A 192.0.2.1", "ok"),
])
def test_dns_requires_the_canary_owner_and_untruncated_answer(flags, record, outcome):
    output = (
        ";; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 1\n"
        f";; flags: {flags}; QUERY: 1, ANSWER: 1\n{record}"
    )
    assert technitium_dns_result(
        {"rc": 0, "stdout": output}, "probe.example.", "192.0.2.1"
    ) == outcome


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


@pytest.mark.parametrize("targets", ["local", "mixed", "unreachable"])
def test_health_playbook_records_current_host_outcomes(tmp_path, targets):
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess

    ansible = shutil.which("ansible-playbook")
    if ansible is None:
        pytest.skip("ansible-playbook is required for the local integration test")

    repo = Path(__file__).resolve().parents[2]
    playbooks = tmp_path / "playbooks"
    shutil.copytree(repo / "playbooks" / "filter_plugins", playbooks / "filter_plugins")
    shutil.copy(repo / "playbooks" / "run_health.yml", playbooks)
    shutil.copytree(repo / "plugins" / "technitium", tmp_path / "plugins" / "technitium")
    commands = tmp_path / "bin"
    commands.mkdir()
    fake_systemctl = commands / "systemctl"
    fake_systemctl.write_text(
        "#!/bin/sh\n"
        "for name do :; done\n"
        "if [ \"$name\" != dns.service ]; then echo LoadState=not-found; exit 1; fi\n"
        "cat <<'UNIT'\n" + unit("dns.service")["stdout"] + "\nUNIT\n"
    )
    fake_dig = commands / "dig"
    fake_dig.write_text(
        "#!/bin/sh\n"
        '[ "$1" = -r ] || exit 2\n'
        "printf '%s\\n' ';; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 1' "
        "'wrong.example. 10 IN A 192.0.2.1'\n"
    )
    for command in (fake_systemctl, fake_dig):
        command.chmod(0o755)

    inventory = tmp_path / "inventory"
    local_host = "fixture ansible_host=127.0.0.1 ansible_connection=local ansible_become=false"
    unreachable_host = (
        "offline ansible_host=127.0.0.1 ansible_connection=ssh "
        "ansible_port=1 ansible_user=test ansible_ssh_timeout=2"
    )
    hosts = {
        "local": [local_host],
        "mixed": [local_host, unreachable_host],
        "unreachable": [unreachable_host],
    }[targets]
    inventory.write_text("\n".join(["[technitium]", *hosts, ""]))
    artifact = tmp_path / "reports" / "health" / "technitium.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(json.dumps({"hosts": [{"hostname": "retired", "health": {
        "status": "HEALTHY", "earned": 10, "possible": 10,
    }}]}))
    process = subprocess.run(
        [
            ansible, "-i", str(inventory), str(playbooks / "run_health.yml"),
            "-e", json.dumps({
                "plugin": "technitium",
                "inventory_group": "technitium",
                "technitium_probe_name": "probe.example",
                "technitium_probe_address": "192.0.2.1",
                "himp_host_bindings": {"offline": {
                    "host_id": 41, "incarnation": 3, "ip": "127.0.0.1", "user": "test",
                }},
            }),
        ],
        cwd=tmp_path,
        env={**os.environ, "PATH": f"{commands}:{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    rows = {row["hostname"]: row for row in json.loads(artifact.read_text())["hosts"]}
    assert set(rows) == {host.split()[0] for host in hosts}
    if targets != "local":
        offline = rows["offline"]
        assert offline["host_identity"] == {"host_id": 41, "incarnation": 3}
        assert offline["health"]["status"] == "UNKNOWN"
        assert offline["report"] == {"collection_status": "unreachable"}
    if targets == "unreachable":
        return
    host = rows["fixture"]
    assert host["report"]["service"] == "dns.service"
    assert host["report"]["dns"] == dict.fromkeys(
        ("local_udp", "local_tcp", "remote_udp", "remote_tcp"), "unexpected_answer"
    )
    assert host["health"]["status"] == "CRITICAL"
    assert "wrong.example" not in artifact.read_text()
