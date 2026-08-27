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


def test_unmapped_attention_returns_none():
    root = Path(__file__).resolve().parents[2]

    service = OperatorGuidanceService(
        root / "config" / "operator_guidance.yml"
    )

    result = service.for_attention(
        {
            "severity": "FAIL",
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
