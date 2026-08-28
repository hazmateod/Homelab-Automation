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
