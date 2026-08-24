import subprocess

import pytest

from himp.services.greenbone import (
    GreenboneClient,
)


REPORT_ID = (
    "71b899c6-12f2-4728-9c8c-6de2e352bc98"
)


def report_xml():
    return f"""
<get_reports_response status="200" status_text="OK">
  <report id="{REPORT_ID}">
    <owner>
      <name>himp-integration</name>
    </owner>

    <report id="{REPORT_ID}">
      <scan_run_status>Done</scan_run_status>

      <task id="task-1">
        <name>Example Task</name>
        <target id="target-1">
          <name>Example Target</name>
        </target>
      </task>

      <scan_start>2026-08-24T18:03:04Z</scan_start>
      <scan_end>2026-08-24T18:10:09Z</scan_end>

      <results start="1" max="-1">
        <result id="result-1">
          <name>Example Finding</name>
          <creation_time>2026-08-24T18:04:00Z</creation_time>
          <modification_time>2026-08-24T18:04:01Z</modification_time>

          <host>
            10.10.37.7
            <asset asset_id="asset-1"/>
            <hostname>unbound107.server.arpa</hostname>
          </host>

          <port>22/tcp</port>

          <nvt oid="1.2.3.4">
            <type>nvt</type>
            <name>Example VT</name>
            <family>General</family>
            <solution type="">Example solution</solution>
          </nvt>

          <scan_nvt_version>2026-08-24T00:00:00Z</scan_nvt_version>
          <threat>Low</threat>
          <severity>2.6</severity>

          <qod>
            <value>80</value>
            <type>remote_banner</type>
          </qod>

          <description>Example description</description>

          <details>
            <result id="nested-reference"/>
          </details>
        </result>
      </results>

      <result_count>1</result_count>
    </report>
  </report>
</get_reports_response>
""".strip()


def test_parse_report_uses_only_direct_results():
    parsed = GreenboneClient.parse_report(
        report_xml()
    )

    assert parsed["report_id"] == REPORT_ID
    assert parsed["owner"] == "himp-integration"
    assert parsed["task_id"] == "task-1"
    assert parsed["target_id"] == "target-1"
    assert parsed["status"] == "Done"
    assert parsed["result_count"] == 1
    assert parsed["maximum_severity"] == 2.6
    assert parsed["threat_counts"] == {
        "Low": 1,
    }

    finding = parsed["findings"][0]

    assert finding["result_id"] == "result-1"
    assert finding["host"] == "10.10.37.7"
    assert (
        finding["hostname"]
        == "unbound107.server.arpa"
    )
    assert finding["asset_id"] == "asset-1"
    assert finding["port"] == "22/tcp"
    assert finding["nvt_oid"] == "1.2.3.4"
    assert finding["severity"] == 2.6
    assert finding["qod"] == 80


def test_parse_report_rejects_result_count_mismatch():
    xml = report_xml().replace(
        "<result_count>1</result_count>",
        "<result_count>2</result_count>",
    )

    with pytest.raises(
        ValueError,
        match="result count mismatch",
    ):
        GreenboneClient.parse_report(
            xml
        )


def test_report_xml_uses_constrained_remote_command(
    monkeypatch,
):
    captured = {}

    def fake_run(
        command,
        **kwargs,
    ):
        captured["command"] = command
        captured["kwargs"] = kwargs

        return subprocess.CompletedProcess(
            command,
            0,
            stdout=report_xml(),
            stderr="",
        )

    monkeypatch.setattr(
        subprocess,
        "run",
        fake_run,
    )

    client = GreenboneClient()

    payload = client.report_xml(
        REPORT_ID
    )

    assert payload.startswith(
        "<get_reports_response"
    )

    command = captured["command"]

    assert command[-5:] == [
        "/usr/bin/sudo",
        "-n",
        "/usr/local/sbin/himp-greenbone",
        "report",
        REPORT_ID,
    ]

    assert (
        "himp-greenbone@10.10.37.62"
        in command
    )


def test_report_xml_rejects_remote_failure(
    monkeypatch,
):
    def fake_run(
        command,
        **kwargs,
    ):
        return subprocess.CompletedProcess(
            command,
            1,
            stdout="",
            stderr="permission denied",
        )

    monkeypatch.setattr(
        subprocess,
        "run",
        fake_run,
    )

    client = GreenboneClient()

    with pytest.raises(
        RuntimeError,
        match="permission denied",
    ):
        client.report_xml(
            REPORT_ID
        )


def completed_reports_output():
    return "\n".join(
        [
            "COMPLETED_REPORT_COUNT=2",
            (
                "COMPLETED_REPORT\t"
                "report-1\t"
                "task-1\t"
                "HIMP - host1 - Full and Fast\t"
                "Done\t"
                "2026-08-24T20:00:00Z\t"
                "2026-08-24T20:10:00Z"
            ),
            (
                "COMPLETED_REPORT\t"
                "report-2\t"
                "task-2\t"
                "HIMP - host2 - Full and Fast\t"
                "Done\t"
                "2026-08-24T20:20:00Z\t"
                "2026-08-24T20:30:00Z"
            ),
        ]
    )


def test_completed_reports_uses_constrained_remote_command(
    monkeypatch,
):
    captured = {}

    def fake_run(
        command,
        **kwargs,
    ):
        captured["command"] = command

        return subprocess.CompletedProcess(
            command,
            0,
            stdout=completed_reports_output(),
            stderr="",
        )

    monkeypatch.setattr(
        subprocess,
        "run",
        fake_run,
    )

    client = GreenboneClient()

    reports = client.completed_reports()

    assert [
        report["report_id"]
        for report in reports
    ] == [
        "report-1",
        "report-2",
    ]

    assert reports[0]["status"] == "Done"

    assert captured["command"][-4:] == [
        "/usr/bin/sudo",
        "-n",
        "/usr/local/sbin/himp-greenbone",
        "completed-reports",
    ]


def test_completed_reports_rejects_count_mismatch(
    monkeypatch,
):
    def fake_run(
        command,
        **kwargs,
    ):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=completed_reports_output().replace(
                "COMPLETED_REPORT_COUNT=2",
                "COMPLETED_REPORT_COUNT=3",
            ),
            stderr="",
        )

    monkeypatch.setattr(
        subprocess,
        "run",
        fake_run,
    )

    client = GreenboneClient()

    with pytest.raises(
        ValueError,
        match="count mismatch",
    ):
        client.completed_reports()


def test_reconcile_host_uses_constrained_remote_command(
    monkeypatch,
):
    captured = {}

    def fake_run(
        command,
        **kwargs,
    ):
        captured["command"] = command

        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(
                "TARGET_CREATED=NO\n"
                "TASK_CREATED=NO\n"
                "SCAN_STARTED=NO\n"
                "HOST_RECONCILE=PASS\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(
        subprocess,
        "run",
        fake_run,
    )

    client = GreenboneClient()

    result = client.reconcile_host(
        "logs.server.arpa",
        "10.10.37.58",
    )

    assert result == {
        "hostname": "logs.server.arpa",
        "address": "10.10.37.58",
        "target_created": False,
        "task_created": False,
        "scan_started": False,
    }

    assert captured["command"][-6:] == [
        "/usr/bin/sudo",
        "-n",
        "/usr/local/sbin/himp-greenbone",
        "host-reconcile",
        "logs.server.arpa",
        "10.10.37.58",
    ]


def test_reconcile_host_rejects_scan_started_contract(
    monkeypatch,
):
    def fake_run(
        command,
        **kwargs,
    ):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(
                "TARGET_CREATED=YES\n"
                "TASK_CREATED=YES\n"
                "SCAN_STARTED=YES\n"
                "HOST_RECONCILE=PASS\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(
        subprocess,
        "run",
        fake_run,
    )

    with pytest.raises(
        RuntimeError,
        match="unexpectedly started",
    ):
        GreenboneClient().reconcile_host(
            "logs.server.arpa",
            "10.10.37.58",
        )
