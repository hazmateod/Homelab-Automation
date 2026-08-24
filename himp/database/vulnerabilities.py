"""
Vulnerability intelligence repository.

Persists normalized Greenbone scan reports and findings while preserving
Greenbone report/result UUIDs as stable external identities.
"""

from himp.database.factory import create_database


class VulnerabilityRepository:
    """
    Durable vulnerability report and finding persistence.
    """

    def __init__(
        self,
        database=None,
    ):
        self.database = (
            database
            if database is not None
            else create_database()
        )

        self.initialize()

    def initialize(self):
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS vulnerability_reports
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                report_id TEXT NOT NULL UNIQUE,

                owner TEXT,

                task_id TEXT,
                task_name TEXT,

                target_id TEXT,
                target_name TEXT,

                status TEXT NOT NULL,

                scan_started_at TIMESTAMP,
                scan_finished_at TIMESTAMP,

                result_count INTEGER NOT NULL,
                maximum_severity REAL NOT NULL,

                log_count INTEGER NOT NULL DEFAULT 0,
                low_count INTEGER NOT NULL DEFAULT 0,
                medium_count INTEGER NOT NULL DEFAULT 0,
                high_count INTEGER NOT NULL DEFAULT 0,
                critical_count INTEGER NOT NULL DEFAULT 0,

                inventory_hostname TEXT,

                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS vulnerability_findings
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                result_id TEXT NOT NULL UNIQUE,

                report_id TEXT NOT NULL,

                inventory_hostname TEXT,

                host TEXT,
                hostname TEXT,
                asset_id TEXT,
                port TEXT,

                name TEXT NOT NULL,

                nvt_oid TEXT,
                nvt_type TEXT,
                nvt_name TEXT,
                nvt_family TEXT,

                severity REAL NOT NULL,
                threat TEXT,

                qod INTEGER,
                qod_type TEXT,

                description TEXT,
                solution TEXT,

                scan_nvt_version TEXT,

                source_created_at TIMESTAMP,
                source_modified_at TIMESTAMP,

                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY(report_id)
                    REFERENCES vulnerability_reports(report_id)
                    ON DELETE CASCADE
            )
            """
        )

        self.database.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_vulnerability_findings_report
            ON vulnerability_findings(report_id)
            """
        )

        self.database.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_vulnerability_findings_inventory_host
            ON vulnerability_findings(inventory_hostname)
            """
        )

        self.database.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_vulnerability_findings_severity
            ON vulnerability_findings(severity)
            """
        )

    def save_report(
        self,
        report,
        inventory_hostname=None,
    ):
        counts = report.get(
            "threat_counts",
            {},
        )

        self.database.execute(
            """
            INSERT INTO vulnerability_reports
            (
                report_id,
                owner,
                task_id,
                task_name,
                target_id,
                target_name,
                status,
                scan_started_at,
                scan_finished_at,
                result_count,
                maximum_severity,
                log_count,
                low_count,
                medium_count,
                high_count,
                critical_count,
                inventory_hostname,
                updated_at
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT(report_id)
            DO UPDATE SET
                owner=excluded.owner,
                task_id=excluded.task_id,
                task_name=excluded.task_name,
                target_id=excluded.target_id,
                target_name=excluded.target_name,
                status=excluded.status,
                scan_started_at=excluded.scan_started_at,
                scan_finished_at=excluded.scan_finished_at,
                result_count=excluded.result_count,
                maximum_severity=excluded.maximum_severity,
                log_count=excluded.log_count,
                low_count=excluded.low_count,
                medium_count=excluded.medium_count,
                high_count=excluded.high_count,
                critical_count=excluded.critical_count,
                inventory_hostname=excluded.inventory_hostname,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                report["report_id"],
                report.get("owner"),
                report.get("task_id"),
                report.get("task_name"),
                report.get("target_id"),
                report.get("target_name"),
                report["status"],
                report.get("scan_started_at"),
                report.get("scan_finished_at"),
                report["result_count"],
                report["maximum_severity"],
                counts.get("Log", 0),
                counts.get("Low", 0),
                counts.get("Medium", 0),
                counts.get("High", 0),
                counts.get("Critical", 0),
                inventory_hostname,
            ),
        )

        return self.report(
            report["report_id"]
        )

    def save_finding(
        self,
        report_id,
        finding,
        inventory_hostname=None,
    ):
        self.database.execute(
            """
            INSERT INTO vulnerability_findings
            (
                result_id,
                report_id,
                inventory_hostname,
                host,
                hostname,
                asset_id,
                port,
                name,
                nvt_oid,
                nvt_type,
                nvt_name,
                nvt_family,
                severity,
                threat,
                qod,
                qod_type,
                description,
                solution,
                scan_nvt_version,
                source_created_at,
                source_modified_at,
                updated_at
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT(result_id)
            DO UPDATE SET
                report_id=excluded.report_id,
                inventory_hostname=excluded.inventory_hostname,
                host=excluded.host,
                hostname=excluded.hostname,
                asset_id=excluded.asset_id,
                port=excluded.port,
                name=excluded.name,
                nvt_oid=excluded.nvt_oid,
                nvt_type=excluded.nvt_type,
                nvt_name=excluded.nvt_name,
                nvt_family=excluded.nvt_family,
                severity=excluded.severity,
                threat=excluded.threat,
                qod=excluded.qod,
                qod_type=excluded.qod_type,
                description=excluded.description,
                solution=excluded.solution,
                scan_nvt_version=excluded.scan_nvt_version,
                source_created_at=excluded.source_created_at,
                source_modified_at=excluded.source_modified_at,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                finding["result_id"],
                report_id,
                inventory_hostname,
                finding.get("host"),
                finding.get("hostname"),
                finding.get("asset_id"),
                finding.get("port"),
                finding["name"],
                finding.get("nvt_oid"),
                finding.get("nvt_type"),
                finding.get("nvt_name"),
                finding.get("nvt_family"),
                finding["severity"],
                finding.get("threat"),
                finding.get("qod"),
                finding.get("qod_type"),
                finding.get("description"),
                finding.get("solution"),
                finding.get("scan_nvt_version"),
                finding.get("created_at") or None,
                finding.get("modified_at") or None,
            ),
        )

        return self.finding(
            finding["result_id"]
        )

    def has_report(
        self,
        report_id,
    ):
        """
        Return whether a Greenbone report UUID is already persisted.
        """
        return (
            self.report(
                report_id
            )
            is not None
        )

    def report(
        self,
        report_id,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM vulnerability_reports
            WHERE report_id=?
            LIMIT 1
            """,
            (
                report_id,
            ),
        )

        if not rows:
            return None

        return dict(
            rows[0]
        )

    def finding(
        self,
        result_id,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM vulnerability_findings
            WHERE result_id=?
            LIMIT 1
            """,
            (
                result_id,
            ),
        )

        if not rows:
            return None

        return dict(
            rows[0]
        )

    def findings_for_report(
        self,
        report_id,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM vulnerability_findings
            WHERE report_id=?
            ORDER BY
                severity DESC,
                name,
                result_id
            """,
            (
                report_id,
            ),
        )

        return [
            dict(row)
            for row in rows
        ]

    def findings_for_host(
        self,
        hostname,
        limit=200,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM vulnerability_findings
            WHERE inventory_hostname=?
            ORDER BY
                severity DESC,
                id DESC
            LIMIT ?
            """,
            (
                hostname,
                limit,
            ),
        )

        return [
            dict(row)
            for row in rows
        ]

    def reports(
        self,
        limit=50,
    ):
        rows = self.database.query(
            """
            SELECT *
            FROM vulnerability_reports
            ORDER BY
                COALESCE(
                    scan_finished_at,
                    scan_started_at,
                    imported_at
                ) DESC,
                id DESC
            LIMIT ?
            """,
            (
                limit,
            ),
        )

        return [
            dict(row)
            for row in rows
        ]

    def report_count(self):
        rows = self.database.query(
            """
            SELECT COUNT(*) AS total
            FROM vulnerability_reports
            """
        )

        return int(
            rows[0]["total"]
        )

    def finding_count(
        self,
        report_id=None,
    ):
        if report_id is None:
            rows = self.database.query(
                """
                SELECT COUNT(*) AS total
                FROM vulnerability_findings
                """
            )
        else:
            rows = self.database.query(
                """
                SELECT COUNT(*) AS total
                FROM vulnerability_findings
                WHERE report_id=?
                """,
                (
                    report_id,
                ),
            )

        return int(
            rows[0]["total"]
        )
