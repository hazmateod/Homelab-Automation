from himp.database.vulnerabilities import (
    VulnerabilityRepository,
)


REPORT_ID = "report-1"
RESULT_ID = "result-1"


def sample_report():
    return {
        "report_id": REPORT_ID,
        "owner": "himp-integration",
        "task_id": "task-1",
        "task_name": "Example Task",
        "target_id": "target-1",
        "target_name": "Example Target",
        "status": "Done",
        "scan_started_at": (
            "2026-08-24T18:03:04"
        ),
        "scan_finished_at": (
            "2026-08-24T18:10:09"
        ),
        "result_count": 1,
        "maximum_severity": 5.9,
        "threat_counts": {
            "Log": 0,
            "Low": 0,
            "Medium": 1,
        },
    }


def sample_finding():
    return {
        "result_id": RESULT_ID,
        "host": "10.10.37.7",
        "hostname": "unbound107.server.arpa",
        "asset_id": "asset-1",
        "port": "22/tcp",
        "name": "Example Finding",
        "nvt_oid": "1.2.3.4",
        "nvt_type": "nvt",
        "nvt_name": "Example VT",
        "nvt_family": "General",
        "severity": 5.9,
        "threat": "Medium",
        "qod": 80,
        "qod_type": "remote_banner",
        "description": "Description",
        "solution": "Solution",
        "scan_nvt_version": "2026-08-24",
        "created_at": None,
        "modified_at": None,
    }


def test_report_and_findings_are_idempotent():
    repository = VulnerabilityRepository()

    report = sample_report()
    finding = sample_finding()

    repository.save_report(
        report,
        inventory_hostname="unbound107",
    )

    repository.save_finding(
        REPORT_ID,
        finding,
        inventory_hostname="unbound107",
    )

    repository.save_report(
        report,
        inventory_hostname="unbound107",
    )

    repository.save_finding(
        REPORT_ID,
        finding,
        inventory_hostname="unbound107",
    )

    assert repository.report_count() == 1

    assert (
        repository.finding_count(
            REPORT_ID
        )
        == 1
    )

    stored_report = repository.report(
        REPORT_ID
    )

    assert (
        stored_report["inventory_hostname"]
        == "unbound107"
    )

    assert (
        stored_report["maximum_severity"]
        == 5.9
    )

    stored_finding = repository.finding(
        RESULT_ID
    )

    assert (
        stored_finding["inventory_hostname"]
        == "unbound107"
    )

    assert (
        stored_finding["severity"]
        == 5.9
    )


def test_findings_for_host():
    repository = VulnerabilityRepository()

    repository.save_report(
        sample_report(),
        inventory_hostname="unbound107",
    )

    repository.save_finding(
        REPORT_ID,
        sample_finding(),
        inventory_hostname="unbound107",
    )

    findings = repository.findings_for_host(
        "unbound107"
    )

    assert len(findings) == 1

    assert (
        findings[0]["result_id"]
        == RESULT_ID
    )
