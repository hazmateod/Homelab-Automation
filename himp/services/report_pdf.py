"""
HIMP PDF Report Service.

Renders the existing operational report data as a PDF.
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class ReportPDFService:

    def generate(self, operational_summary):

        buffer = BytesIO()

        document = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
            title="HIMP Operational Report",
            author="HIMP",
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            spaceAfter=12,
        )

        heading_style = ParagraphStyle(
            "ReportHeading",
            parent=styles["Heading2"],
            spaceBefore=12,
            spaceAfter=8,
        )

        body_style = styles["BodyText"]

        story = [
            Paragraph(
                "HIMP Operational Report",
                title_style,
            ),
            Paragraph(
                self._text(
                    "Generated",
                    operational_summary.get("generated"),
                ),
                body_style,
            ),
            Spacer(1, 12),
        ]

        dashboard = operational_summary.get(
            "dashboard"
        )

        story.append(
            Paragraph(
                "Dashboard Summary",
                heading_style,
            )
        )

        if dashboard:

            story.append(
                self._table(
                    [
                        ["Metric", "Value"],
                        ["Hosts", dashboard.get("hosts", 0)],
                        ["Healthy", dashboard.get("healthy", 0)],
                        ["Warnings", dashboard.get("warnings", 0)],
                        ["Critical", dashboard.get("critical", 0)],
                        ["Unknown", dashboard.get("unknown", 0)],
                        [
                            "Average Score",
                            dashboard.get(
                                "average_score",
                                0,
                            ),
                        ],
                    ]
                )
            )

        else:

            story.append(
                Paragraph(
                    "No dashboard report is currently available.",
                    body_style,
                )
            )

        reports = operational_summary.get(
            "reports",
            {},
        )

        story.append(
            Paragraph(
                "Report Inventory",
                heading_style,
            )
        )

        if reports:

            story.append(
                self._table(
                    [
                        ["Report Type", "Files"],
                        *[
                            [name, count]
                            for name, count in reports.items()
                        ],
                    ]
                )
            )

        else:

            story.append(
                Paragraph(
                    "No report files are currently available.",
                    body_style,
                )
            )

        executions = operational_summary.get(
            "executions",
            {},
        )

        story.append(
            Paragraph(
                "Execution Summary",
                heading_style,
            )
        )

        story.append(
            self._table(
                [
                    ["Metric", "Value"],
                    [
                        "Total Executions",
                        executions.get("total", 0),
                    ],
                    [
                        "Successful",
                        executions.get(
                            "successful",
                            0,
                        ),
                    ],
                    [
                        "Failed",
                        executions.get(
                            "failed",
                            0,
                        ),
                    ],
                ]
            )
        )

        recent = executions.get(
            "recent",
            [],
        )

        story.append(
            Paragraph(
                "Recent Execution History",
                heading_style,
            )
        )

        if recent:

            rows = [
                [
                    "ID",
                    "Task",
                    "Status",
                    "Elapsed",
                    "Executed",
                ]
            ]

            for execution in recent:

                rows.append(
                    [
                        execution.get("id"),
                        execution.get("task_id"),
                        (
                            "Successful"
                            if execution.get("success")
                            else "Failed"
                        ),
                        f'{execution.get("elapsed", 0)}s',
                        execution.get(
                            "executed_at"
                        ),
                    ]
                )

            story.append(
                self._table(
                    rows,
                    widths=[
                        0.5 * inch,
                        1.4 * inch,
                        1.0 * inch,
                        0.8 * inch,
                        2.8 * inch,
                    ],
                    repeat_rows=1,
                )
            )

        else:

            story.append(
                Paragraph(
                    "No automation execution history is currently available.",
                    body_style,
                )
            )

        document.build(story)

        return buffer.getvalue()

    @staticmethod
    def _text(label, value):

        return f"{label}: {value}"

    @staticmethod
    def _table(
        rows,
        widths=None,
        repeat_rows=0,
    ):

        table = Table(
            rows,
            colWidths=widths,
            repeatRows=repeat_rows,
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
                        "PADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                ]
            )
        )

        return table
