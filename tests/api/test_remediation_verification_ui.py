from pathlib import Path


def test_remediation_ui_exposes_execution_and_verification_separately():
    content = Path(
        "templates/remediation.html"
    ).read_text()

    assert "<th>Execution</th>" in content

    assert (
        "<th>Verification</th>"
        in content
    )

    assert (
        "verification_status"
        in content
    )

    assert (
        "verification_success"
        in content
    )

    assert (
        "Verification Evidence"
        in content
    )


def test_remediation_summary_exposes_verification_counts():
    content = Path(
        "templates/components/"
        "remediation_summary.html"
    ).read_text()

    assert (
        "verification_success_count"
        in content
    )

    assert (
        "verification_failure_count"
        in content
    )

    assert (
        "verification_not_supported_count"
        in content
    )
