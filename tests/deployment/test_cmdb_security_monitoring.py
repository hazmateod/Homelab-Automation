from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

SECURITY = ROOT / "roles/cmdb/tasks/security.yml"
MONITORING = ROOT / "roles/cmdb/tasks/monitoring.yml"
ASSEMBLE = ROOT / "roles/cmdb/tasks/assemble.yml"
MAIN = ROOT / "roles/cmdb/tasks/main.yml"


def test_cmdb_security_collector_exists_and_is_read_only():
    source = SECURITY.read_text()

    assert "cmdb_security:" in source
    assert "ssh:" in source
    assert "apparmor:" in source
    assert "auditd:" in source
    assert "fail2ban:" in source
    assert "aide:" in source
    assert "unattended_upgrades:" in source
    assert "firewall:" in source

    forbidden = (
        "ansible.builtin.package:",
        "ansible.builtin.apt:",
        "ansible.builtin.service:",
        "ansible.builtin.systemd:",
    )

    for token in forbidden:
        assert token not in source


def test_cmdb_security_collector_tolerates_missing_controls():
    source = SECURITY.read_text()

    assert "failed_when: false" in source
    assert "not-found" in source
    assert "none_detected" in source


def test_cmdb_monitoring_collector_exists_and_is_read_only():
    source = MONITORING.read_text()

    assert "cmdb_monitoring:" in source
    assert "uptime:" in source
    assert "observed_at:" in source
    assert "load:" in source
    assert "system:" in source
    assert "time_sync:" in source
    assert "agents:" in source

    forbidden = (
        "ansible.builtin.package:",
        "ansible.builtin.apt:",
        "ansible.builtin.service:",
        "ansible.builtin.systemd:",
    )

    for token in forbidden:
        assert token not in source


def test_cmdb_monitoring_records_operational_signals():
    source = MONITORING.read_text()

    assert "/proc/uptime" in source
    assert "ansible_loadavg" in source
    assert "systemctl is-system-running" in source
    assert "systemctl --failed" in source
    assert "chrony.service" in source
    assert "systemd-timesyncd.service" in source


def test_cmdb_main_runs_security_and_monitoring_collectors():
    source = MAIN.read_text()

    assert "- import_tasks: security.yml" in source
    assert "- import_tasks: monitoring.yml" in source

    assert source.index("- import_tasks: security.yml") < source.index(
        "- import_tasks: monitoring.yml"
    )


def test_cmdb_assembly_preserves_security_and_monitoring():
    source = ASSEMBLE.read_text()

    assert "security: \"{{ cmdb_security | default({}) }}\"" in source
    assert (
        "monitoring: \"{{ cmdb_monitoring | default({}) }}\""
        in source
    )
