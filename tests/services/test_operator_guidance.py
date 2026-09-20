from pathlib import Path

import pytest

from himp.services.operator_guidance import (
    OperatorGuidanceService,
)


def write_catalog(
    tmp_path,
    content,
):
    path = tmp_path / "operator_guidance.yml"
    path.write_text(
        content,
        encoding="utf-8",
    )
    return path


def test_loads_reviewed_guidance_catalog():
    root = Path(__file__).resolve().parents[2]

    service = OperatorGuidanceService(
        root / "config" / "operator_guidance.yml"
    )

    result = service.load()

    assert "host_connectivity_failed" in result
    assert "host_connectivity_warning" in result

    failed = result[
        "host_connectivity_failed"
    ]

    assert failed["category"] == "Host Connectivity"
    assert failed["severity"] == "FAIL"
    assert (
        failed["urgency"]
        == "CHECK_WHEN_CONVENIENT"
    )
    assert failed["safe_actions"]
    assert failed["do_not"]
    assert failed["detail_href"] == "/health"


def test_maps_failed_host_connectivity_attention():
    root = Path(__file__).resolve().parents[2]

    service = OperatorGuidanceService(
        root / "config" / "operator_guidance.yml"
    )

    result = service.for_attention(
        {
            "severity": "FAIL",
            "category": "Host Connectivity",
        }
    )

    assert result is not None
    assert (
        result["id"]
        == "host_connectivity_failed"
    )
    assert result["severity"] == "FAIL"


def test_maps_warning_host_connectivity_attention():
    root = Path(__file__).resolve().parents[2]

    service = OperatorGuidanceService(
        root / "config" / "operator_guidance.yml"
    )

    result = service.for_attention(
        {
            "severity": "WARNING",
            "category": "Host Connectivity",
        }
    )

    assert result is not None
    assert (
        result["id"]
        == "host_connectivity_warning"
    )
    assert result["severity"] == "WARNING"


def test_unsupported_attention_returns_none():
    root = Path(__file__).resolve().parents[2]

    service = OperatorGuidanceService(
        root / "config" / "operator_guidance.yml"
    )

    result = service.for_attention(
        {
            "severity": "WARNING",
            "category": "Automation",
        }
    )

    assert result is None


def test_rejects_missing_required_fields(
    tmp_path,
):
    path = write_catalog(
        tmp_path,
        """
guidance:
  broken:
    category: Host Connectivity
""",
    )

    service = OperatorGuidanceService(
        path
    )

    with pytest.raises(
        ValueError,
        match="missing fields",
    ):
        service.load()


def test_rejects_invalid_urgency(
    tmp_path,
):
    path = write_catalog(
        tmp_path,
        """
guidance:
  broken:
    category: Host Connectivity
    severity: FAIL
    title: Broken
    urgency: PANIC
    summary: Summary
    meaning: Meaning
    affects: Affected system.
    resolved_when: HIMP reports recovery.
    safe_actions:
      - Check something.
    can_wait: Yes.
    do_not:
      - Do not panic.
    escalation: Get help.
    detail_href: /health
""",
    )

    service = OperatorGuidanceService(
        path
    )

    with pytest.raises(
        ValueError,
        match="unsupported urgency",
    ):
        service.load()


def test_rejects_empty_action_lists(
    tmp_path,
):
    path = write_catalog(
        tmp_path,
        """
guidance:
  broken:
    category: Host Connectivity
    severity: FAIL
    title: Broken
    urgency: GET_TECHNICAL_HELP
    summary: Summary
    meaning: Meaning
    affects: Affected system.
    resolved_when: HIMP reports recovery.
    safe_actions: []
    can_wait: No.
    do_not:
      - Do not change anything.
    escalation: Get help.
    detail_href: /health
""",
    )

    service = OperatorGuidanceService(
        path
    )

    with pytest.raises(
        ValueError,
        match="safe_actions",
    ):
        service.load()


def test_for_attention_maps_workflow_failure(
    tmp_path,
):
    service = OperatorGuidanceService(
        "config/operator_guidance.yml"
    )

    result = service.for_attention(
        {
            "category": "Workflow",
            "severity": "FAIL",
        }
    )

    assert result["id"] == "workflow_failed"
    assert result["urgency"] == "CHECK_WHEN_CONVENIENT"


def test_for_attention_maps_automation_failure(
    tmp_path,
):
    service = OperatorGuidanceService(
        "config/operator_guidance.yml"
    )

    result = service.for_attention(
        {
            "category": "Automation",
            "severity": "FAIL",
        }
    )

    assert result["id"] == "automation_failed"
    assert result["urgency"] == "CHECK_WHEN_CONVENIENT"


def test_for_attention_maps_remediation_execution_failure(
    tmp_path,
):
    service = OperatorGuidanceService(
        "config/operator_guidance.yml"
    )

    result = service.for_attention(
        {
            "category": "Remediation",
            "severity": "FAIL",
        }
    )

    assert (
        result["id"]
        == "remediation_execution_failed"
    )
    assert result["urgency"] == "GET_TECHNICAL_HELP"


def test_for_attention_maps_remediation_confirmation_warning(
    tmp_path,
):
    service = OperatorGuidanceService(
        "config/operator_guidance.yml"
    )

    result = service.for_attention(
        {
            "category": "Remediation",
            "severity": "WARNING",
        }
    )

    assert (
        result["id"]
        == "remediation_confirmation_required"
    )
    assert result["urgency"] == "NO_ACTION_NEEDED"


def test_for_attention_rejects_unsupported_product_condition(
    tmp_path,
):
    service = OperatorGuidanceService(
        "config/operator_guidance.yml"
    )

    assert service.for_attention(
        {
            "category": "Workflow",
            "severity": "WARNING",
        }
    ) is None


def test_safe_for_attention_returns_none_when_catalog_missing(
    tmp_path,
):
    service = OperatorGuidanceService(
        tmp_path / "missing.yml"
    )

    result = service.safe_for_attention(
        {
            "category": "Automation",
            "severity": "FAIL",
        }
    )

    assert result is None


def test_safe_for_attention_returns_none_for_malformed_catalog(
    tmp_path,
):
    path = tmp_path / "operator_guidance.yml"

    path.write_text(
        "guidance: [broken",
        encoding="utf-8",
    )

    service = OperatorGuidanceService(
        path
    )

    result = service.safe_for_attention(
        {
            "category": "Automation",
            "severity": "FAIL",
        }
    )

    assert result is None


def test_strict_lookup_still_rejects_missing_catalog(
    tmp_path,
):
    service = OperatorGuidanceService(
        tmp_path / "missing.yml"
    )

    with pytest.raises(
        FileNotFoundError
    ):
        service.for_attention(
            {
                "category": "Automation",
                "severity": "FAIL",
            }
        )


@pytest.mark.parametrize(
    "group",
    [
        "technitium",
        "unbound",
        "pihole",
    ],
)
def test_failed_dns_host_uses_dns_guidance(
    group,
):
    service = OperatorGuidanceService(
        "config/operator_guidance.yml"
    )

    result = service.for_attention(
        {
            "category": "Host Connectivity",
            "severity": "FAIL",
            "affected_hosts": [
                {
                    "hostname": "dns-host",
                    "group": group,
                    "ip": "192.0.2.10",
                },
            ],
        }
    )

    assert result["id"] == "dns_connectivity_failed"
    assert result["urgency"] == "ACTION_RECOMMENDED"


def test_warning_dns_host_uses_dns_guidance():
    service = OperatorGuidanceService(
        "config/operator_guidance.yml"
    )

    result = service.for_attention(
        {
            "category": "Host Connectivity",
            "severity": "WARNING",
            "affected_hosts": [
                {
                    "hostname": "unbound108",
                    "group": "unbound",
                    "ip": "10.10.37.8",
                },
            ],
        }
    )

    assert result["id"] == "dns_connectivity_warning"
    assert result["urgency"] == "CHECK_WHEN_CONVENIENT"


def test_multiple_dns_groups_use_dns_guidance():
    service = OperatorGuidanceService(
        "config/operator_guidance.yml"
    )

    result = service.for_attention(
        {
            "category": "Host Connectivity",
            "severity": "FAIL",
            "affected_hosts": [
                {
                    "hostname": "dns1009",
                    "group": "technitium",
                    "ip": "10.10.37.9",
                },
                {
                    "hostname": "unbound108",
                    "group": "unbound",
                    "ip": "10.10.37.8",
                },
            ],
        }
    )

    assert result["id"] == "dns_connectivity_failed"


def test_mixed_host_groups_use_generic_connectivity_guidance():
    service = OperatorGuidanceService(
        "config/operator_guidance.yml"
    )

    result = service.for_attention(
        {
            "category": "Host Connectivity",
            "severity": "FAIL",
            "affected_hosts": [
                {
                    "hostname": "dns1009",
                    "group": "technitium",
                    "ip": "10.10.37.9",
                },
                {
                    "hostname": "plex",
                    "group": "media",
                    "ip": "192.168.10.50",
                },
            ],
        }
    )

    assert result["id"] == "host_connectivity_failed"


def test_missing_host_evidence_uses_generic_connectivity_guidance():
    service = OperatorGuidanceService(
        "config/operator_guidance.yml"
    )

    result = service.for_attention(
        {
            "category": "Host Connectivity",
            "severity": "FAIL",
        }
    )

    assert result["id"] == "host_connectivity_failed"


def test_host_guidance_domain_identifies_dns_groups():
    assert (
        OperatorGuidanceService._host_guidance_domain(
            {
                "affected_hosts": [
                    {
                        "hostname": "dns1009",
                        "group": "technitium",
                    },
                    {
                        "hostname": "unbound108",
                        "group": "unbound",
                    },
                ],
            }
        )
        == "dns"
    )


def test_host_guidance_domain_rejects_mixed_domains():
    assert (
        OperatorGuidanceService._host_guidance_domain(
            {
                "affected_hosts": [
                    {
                        "hostname": "dns1009",
                        "group": "technitium",
                    },
                    {
                        "hostname": "plex",
                        "group": "media",
                    },
                ],
            }
        )
        is None
    )


def test_host_guidance_domain_rejects_missing_evidence():
    assert (
        OperatorGuidanceService._host_guidance_domain(
            {}
        )
        is None
    )


def test_host_guidance_domain_rejects_malformed_evidence():
    assert (
        OperatorGuidanceService._host_guidance_domain(
            {
                "affected_hosts": "dns1009",
            }
        )
        is None
    )


@pytest.mark.parametrize(
    (
        "group",
        "domain",
        "fail_id",
        "warning_id",
    ),
    [
        (
            "backup",
            "backup",
            "backup_connectivity_failed",
            "backup_connectivity_warning",
        ),
        (
            "proxmox",
            "virtualization",
            "virtualization_connectivity_failed",
            "virtualization_connectivity_warning",
        ),
        (
            "media",
            "media",
            "media_connectivity_failed",
            "media_connectivity_warning",
        ),
        (
            "vpn",
            "vpn",
            "vpn_connectivity_failed",
            "vpn_connectivity_warning",
        ),
    ],
)
def test_inventory_domain_guidance_mapping(
    group,
    domain,
    fail_id,
    warning_id,
):
    service = OperatorGuidanceService(
        "config/operator_guidance.yml"
    )

    attention = {
        "category": "Host Connectivity",
        "affected_hosts": [
            {
                "hostname": "example-host",
                "group": group,
                "ip": "192.0.2.20",
            },
        ],
    }

    assert (
        service._host_guidance_domain(
            attention
        )
        == domain
    )

    attention["severity"] = "FAIL"

    assert (
        service.for_attention(
            attention
        )["id"]
        == fail_id
    )

    attention["severity"] = "WARNING"

    assert (
        service.for_attention(
            attention
        )["id"]
        == warning_id
    )


def test_different_inventory_domains_fall_back_to_generic_guidance():
    service = OperatorGuidanceService(
        "config/operator_guidance.yml"
    )

    result = service.for_attention(
        {
            "category": "Host Connectivity",
            "severity": "FAIL",
            "affected_hosts": [
                {
                    "hostname": "pbs01",
                    "group": "backup",
                    "ip": "10.10.37.52",
                },
                {
                    "hostname": "pve01",
                    "group": "proxmox",
                    "ip": "10.10.37.50",
                },
            ],
        }
    )

    assert result["id"] == "host_connectivity_failed"


def test_telephony_fail_uses_critical_continuity_guidance():
    service = OperatorGuidanceService(
        "config/operator_guidance.yml"
    )

    attention = {
        "category": "Host Connectivity",
        "severity": "FAIL",
        "affected_hosts": [
            {
                "hostname": "freepbx",
                "group": "telephony",
                "ip": "10.10.37.70",
            },
        ],
    }

    assert (
        service._host_guidance_domain(
            attention
        )
        == "telephony"
    )

    result = service.for_attention(
        attention
    )

    assert (
        result["id"]
        == "telephony_connectivity_failed"
    )

    assert (
        result["urgency"]
        == "GET_TECHNICAL_HELP"
    )


def test_telephony_warning_uses_telephony_guidance():
    service = OperatorGuidanceService(
        "config/operator_guidance.yml"
    )

    result = service.for_attention(
        {
            "category": "Host Connectivity",
            "severity": "WARNING",
            "affected_hosts": [
                {
                    "hostname": "freepbx",
                    "group": "telephony",
                    "ip": "10.10.37.70",
                },
            ],
        }
    )

    assert (
        result["id"]
        == "telephony_connectivity_warning"
    )

    assert (
        result["urgency"]
        == "ACTION_RECOMMENDED"
    )
