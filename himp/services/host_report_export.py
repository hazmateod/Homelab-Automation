"""
HIMP Host Report Export Service.

Provides host-specific TXT, CSV, and PDF exports from the
existing generated host report data.
"""

import csv
import io
import json
from html import escape
from pathlib import Path
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from himp.database.inventory import InventoryRepository
from himp.database.host_identity import HostIdentityRepository


class HostReportExportService:

    def __init__(self):
        self.root = Path("reports")
        self.inventory = InventoryRepository()
        self.identities = HostIdentityRepository(self.inventory)

    def report(self, hostname):
        host = self.inventory.find_host(hostname)

        if host is None:
            raise ValueError(
                f"Inventory host not found: {hostname}"
            )

        filename = (
            self.root
            / "current"
            / "cmdb"
            / f"{hostname}.md"
        )

        bindings = self.identities.report_bindings()
        candidates = [filename, filename.parent / "unverified" / filename.name]
        binding = bindings.get(hostname)
        if binding is not None:
            history = self.root / "history" / "cmdb" / str(UUID(binding["host_id"]))
            candidates.append(history / str(binding["incarnation"]) / "report.md")
            # Pre-archive exports still live under their original verified alias.
            for alias in reversed(self.identities.aliases(binding["host_id"])):
                old_name = alias["old_hostname"]
                if old_name and Path(old_name).name == old_name:
                    candidates.append(filename.with_name(f"{old_name}.md"))
        for candidate in candidates:
            try:
                content = candidate.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            first_line, _, remainder = content.partition("\n")
            identity = None
            prefix = "<!-- himp-host-identity: "
            if first_line.startswith(prefix):
                try:
                    identity = json.loads(first_line.removeprefix(prefix).removesuffix(" -->"))
                except ValueError:
                    continue
                if not isinstance(identity, dict):
                    continue
                content = remainder
            if HostIdentityRepository.report_matches(bindings, hostname, identity):
                heading, newline, body = content.partition("\n")
                if heading.startswith("# ") and heading.endswith(" Infrastructure Report"):
                    content = f"# {hostname} Infrastructure Report{newline}{body}"
                break
        else:
            raise FileNotFoundError(f"Host report not found: {hostname}")

        return {
            "hostname": hostname,
            "content": content,
            "rows": self._parse(content),
        }

    def history(self, hostname, incarnation, extension="md"):
        host = self.inventory.find_host(hostname, include_inactive=True)
        host_id = self.identities.identifier(host["id"]) if host else None
        if host_id is None or incarnation < 1 or extension not in {"md", "json"}:
            raise FileNotFoundError(f"Historical host report not found: {hostname}")
        directory = self.root / "history" / "cmdb" / str(UUID(host_id)) / str(incarnation)
        return (directory / f"report.{extension}").read_text(encoding="utf-8")

    def txt(self, hostname):
        return self.report(hostname)["content"].encode(
            "utf-8"
        )

    def csv(self, hostname):
        report = self.report(hostname)

        buffer = io.StringIO(
            newline=""
        )

        writer = csv.writer(buffer)

        writer.writerow(
            [
                "hostname",
                "section",
                "metric",
                "value",
            ]
        )

        for row in report["rows"]:
            writer.writerow(
                [
                    report["hostname"],
                    row["section"],
                    row["metric"],
                    row["value"],
                ]
            )

        return buffer.getvalue().encode(
            "utf-8"
        )

    def pdf(self, hostname):
        report = self.report(hostname)

        buffer = io.BytesIO()

        document = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.5 * 72,
            leftMargin=0.5 * 72,
            topMargin=0.5 * 72,
            bottomMargin=0.5 * 72,
            title=f"HIMP Host Report - {hostname}",
            author="HIMP",
        )

        styles = getSampleStyleSheet()

        title_style = styles["Title"]

        body_style = styles["BodyText"]
        body_style.fontSize = 8
        body_style.leading = 10
        body_style.spaceAfter = 0

        header_style = styles["Heading4"]
        header_style.fontSize = 8
        header_style.leading = 10
        header_style.textColor = colors.white

        story = [
            Paragraph(
                f"HIMP Host Report - {escape(hostname)}",
                title_style,
            ),
            Spacer(1, 12),
        ]

        def cell(value):
            return Paragraph(
                escape(str(value)).replace("\n", "<br/>"),
                body_style,
            )

        rows = [
            [
                Paragraph("Section", header_style),
                Paragraph("Metric", header_style),
                Paragraph("Value", header_style),
            ]
        ]

        for row in report["rows"]:
            rows.append(
                [
                    cell(row["section"]),
                    cell(row["metric"]),
                    cell(row["value"]),
                ]
            )

        if len(rows) == 1:
            rows.append(
                [
                    cell("Report"),
                    cell("Content"),
                    cell(
                        "No structured report data available."
                    ),
                ]
            )

        table = Table(
            rows,
            colWidths=[
                1.35 * 72,
                1.65 * 72,
                4.25 * 72,
            ],
            repeatRows=1,
            hAlign="LEFT",
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#343a40"),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.grey,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),
                ]
            )
        )

        story.append(table)

        document.build(story)

        return buffer.getvalue()

    @staticmethod
    def _parse(content):
        section = "Report"
        rows = []

        lines = content.splitlines()
        index = 0

        while index < len(lines):
            line = lines[index].strip()

            if line.startswith("#"):
                section = line.lstrip("#").strip()
                index += 1
                continue

            if not line or line == "---":
                index += 1
                continue

            if (
                index + 1 < len(lines)
                and lines[index + 1].strip()
                and not lines[index + 1].strip().startswith("#")
                and lines[index + 1].strip() != "---"
            ):
                rows.append(
                    {
                        "section": section,
                        "metric": line.rstrip(":"),
                        "value": lines[
                            index + 1
                        ].strip(),
                    }
                )

                index += 2
                continue

            index += 1

        return rows
