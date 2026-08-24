"""
Greenbone integration client.

Provides the constrained HIMP-side read path to the dedicated
Greenbone integration identity.

This service does not expose arbitrary remote commands. The remote
launcher remains responsible for enforcing the Greenbone command
boundary.
"""

from __future__ import annotations

from collections import Counter
import subprocess
import xml.etree.ElementTree as ET


class GreenboneClient:
    """
    Read-only client for the dedicated Greenbone integration endpoint.
    """

    HOST = "10.10.37.62"
    USER = "himp-greenbone"
    IDENTITY_FILE = "/var/lib/himp/.ssh/id_ed25519"

    CONNECT_TIMEOUT = 10
    COMMAND_TIMEOUT = 60

    REPORT_COMMAND = (
        "/usr/bin/sudo",
        "-n",
        "/usr/local/sbin/himp-greenbone",
        "report",
    )

    def __init__(
        self,
        host=None,
        user=None,
        identity_file=None,
    ):
        self.host = host or self.HOST
        self.user = user or self.USER
        self.identity_file = (
            identity_file
            or self.IDENTITY_FILE
        )

    def _ssh_command(
        self,
        remote_command,
    ):
        return [
            "/usr/bin/ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "PasswordAuthentication=no",
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            (
                "ConnectTimeout="
                f"{self.CONNECT_TIMEOUT}"
            ),
            "-i",
            self.identity_file,
            f"{self.user}@{self.host}",
            *remote_command,
        ]

    def report_xml(
        self,
        report_id,
        timeout=None,
    ):
        """
        Retrieve one Greenbone report through the constrained remote helper.
        """
        if (
            not isinstance(report_id, str)
            or not report_id.strip()
        ):
            raise ValueError(
                "report_id is required"
            )

        command = self._ssh_command(
            (
                *self.REPORT_COMMAND,
                report_id,
            )
        )

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=(
                    timeout
                    if timeout is not None
                    else self.COMMAND_TIMEOUT
                ),
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                "Greenbone report retrieval timed out"
            ) from exc

        if process.returncode != 0:
            message = (
                process.stderr.strip()
                or process.stdout.strip()
                or (
                    "Greenbone report retrieval "
                    f"failed with rc={process.returncode}"
                )
            )

            raise RuntimeError(
                message
            )

        payload = process.stdout.strip()

        if not payload:
            raise RuntimeError(
                "Greenbone returned an empty report"
            )

        return payload

    @staticmethod
    def parse_report(
        xml_text,
    ):
        """
        Normalize one complete GMP report.

        Only direct <results>/<result> children are findings.
        Nested result references are intentionally ignored.
        """
        if (
            not isinstance(xml_text, str)
            or not xml_text.strip()
        ):
            raise ValueError(
                "Greenbone report XML is required"
            )

        try:
            root = ET.fromstring(
                xml_text.strip()
            )
        except ET.ParseError as exc:
            raise ValueError(
                "Greenbone report XML is invalid"
            ) from exc

        if root.tag != "get_reports_response":
            raise ValueError(
                "Unexpected Greenbone report response"
            )

        if root.attrib.get("status") != "200":
            raise RuntimeError(
                "Greenbone report response was not successful"
            )

        outer_report = root.find(
            "./report"
        )

        if outer_report is None:
            raise ValueError(
                "Greenbone outer report is missing"
            )

        scan_report = outer_report.find(
            "./report"
        )

        if scan_report is None:
            raise ValueError(
                "Greenbone scan report is missing"
            )

        results_container = scan_report.find(
            "./results"
        )

        if results_container is None:
            raise ValueError(
                "Greenbone results container is missing"
            )

        report_id = scan_report.attrib.get(
            "id",
            "",
        )

        outer_report_id = outer_report.attrib.get(
            "id",
            "",
        )

        if (
            not report_id
            or report_id != outer_report_id
        ):
            raise ValueError(
                "Greenbone report identity mismatch"
            )

        task = scan_report.find(
            "./task"
        )

        target = (
            task.find("./target")
            if task is not None
            else None
        )

        owner = outer_report.findtext(
            "./owner/name",
            default="",
        ).strip()

        result_count_text = scan_report.findtext(
            "./result_count",
            default="0",
        ).strip()

        try:
            expected_result_count = int(
                result_count_text or "0"
            )
        except ValueError as exc:
            raise ValueError(
                "Greenbone result_count is invalid"
            ) from exc

        findings = []

        for result in results_container.findall(
            "./result"
        ):
            result_id = result.attrib.get(
                "id",
                "",
            ).strip()

            nvt = result.find(
                "./nvt"
            )

            host = result.find(
                "./host"
            )

            qod = result.find(
                "./qod"
            )

            if not result_id:
                raise ValueError(
                    "Greenbone result is missing an id"
                )

            if nvt is None:
                raise ValueError(
                    "Greenbone result is missing NVT metadata"
                )

            severity_text = (
                result.findtext(
                    "./severity",
                    default="",
                )
                or ""
            ).strip()

            try:
                severity = float(
                    severity_text
                )
            except ValueError as exc:
                raise ValueError(
                    "Greenbone result severity is invalid"
                ) from exc

            qod_text = ""

            qod_type = ""

            if qod is not None:
                qod_text = (
                    qod.findtext(
                        "./value",
                        default="",
                    )
                    or ""
                ).strip()

                qod_type = (
                    qod.findtext(
                        "./type",
                        default="",
                    )
                    or ""
                ).strip()

            try:
                qod_value = (
                    int(qod_text)
                    if qod_text
                    else None
                )
            except ValueError as exc:
                raise ValueError(
                    "Greenbone result QoD is invalid"
                ) from exc

            asset_id = None
            hostname = ""

            if host is not None:
                asset = host.find(
                    "./asset"
                )

                if asset is not None:
                    asset_id = asset.attrib.get(
                        "asset_id"
                    )

                hostname = (
                    host.findtext(
                        "./hostname",
                        default="",
                    )
                    or ""
                ).strip()

            findings.append(
                {
                    "result_id": result_id,
                    "host": (
                        (host.text or "").strip()
                        if host is not None
                        else ""
                    ),
                    "hostname": hostname,
                    "asset_id": asset_id,
                    "port": (
                        result.findtext(
                            "./port",
                            default="",
                        )
                        or ""
                    ).strip(),
                    "name": (
                        result.findtext(
                            "./name",
                            default="",
                        )
                        or ""
                    ).strip(),
                    "nvt_oid": nvt.attrib.get(
                        "oid",
                        "",
                    ).strip(),
                    "nvt_type": (
                        nvt.findtext(
                            "./type",
                            default="",
                        )
                        or ""
                    ).strip(),
                    "nvt_name": (
                        nvt.findtext(
                            "./name",
                            default="",
                        )
                        or ""
                    ).strip(),
                    "nvt_family": (
                        nvt.findtext(
                            "./family",
                            default="",
                        )
                        or ""
                    ).strip(),
                    "severity": severity,
                    "threat": (
                        result.findtext(
                            "./threat",
                            default="",
                        )
                        or ""
                    ).strip(),
                    "qod": qod_value,
                    "qod_type": qod_type,
                    "description": (
                        result.findtext(
                            "./description",
                            default="",
                        )
                        or ""
                    ).strip(),
                    "solution": (
                        nvt.findtext(
                            "./solution",
                            default="",
                        )
                        or ""
                    ).strip(),
                    "scan_nvt_version": (
                        result.findtext(
                            "./scan_nvt_version",
                            default="",
                        )
                        or ""
                    ).strip(),
                    "created_at": (
                        result.findtext(
                            "./creation_time",
                            default="",
                        )
                        or ""
                    ).strip(),
                    "modified_at": (
                        result.findtext(
                            "./modification_time",
                            default="",
                        )
                        or ""
                    ).strip(),
                }
            )

        ids = [
            item["result_id"]
            for item in findings
        ]

        if len(ids) != len(set(ids)):
            raise ValueError(
                "Greenbone report contains duplicate direct result IDs"
            )

        if len(findings) != expected_result_count:
            raise ValueError(
                "Greenbone report result count mismatch: "
                f"expected {expected_result_count}, "
                f"parsed {len(findings)}"
            )

        threat_counts = Counter(
            item["threat"] or "Unknown"
            for item in findings
        )

        severity_max = max(
            (
                item["severity"]
                for item in findings
            ),
            default=0.0,
        )

        return {
            "report_id": report_id,
            "owner": owner,
            "task_id": (
                task.attrib.get(
                    "id",
                    "",
                )
                if task is not None
                else ""
            ),
            "task_name": (
                task.findtext(
                    "./name",
                    default="",
                ).strip()
                if task is not None
                else ""
            ),
            "target_id": (
                target.attrib.get(
                    "id",
                    "",
                )
                if target is not None
                else ""
            ),
            "target_name": (
                target.findtext(
                    "./name",
                    default="",
                ).strip()
                if target is not None
                else ""
            ),
            "status": (
                scan_report.findtext(
                    "./scan_run_status",
                    default="",
                )
                or ""
            ).strip(),
            "scan_started_at": (
                scan_report.findtext(
                    "./scan_start",
                    default="",
                )
                or ""
            ).strip(),
            "scan_finished_at": (
                scan_report.findtext(
                    "./scan_end",
                    default="",
                )
                or ""
            ).strip(),
            "result_count": len(
                findings
            ),
            "maximum_severity": severity_max,
            "threat_counts": dict(
                threat_counts
            ),
            "findings": findings,
        }

    def report(
        self,
        report_id,
        timeout=None,
    ):
        return self.parse_report(
            self.report_xml(
                report_id,
                timeout=timeout,
            )
        )
