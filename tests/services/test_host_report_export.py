from himp.services.host_report_export import (
    HostReportExportService,
)


def make_report(tmp_path):
    root = tmp_path / "reports"
    report_dir = root / "current" / "cmdb"
    report_dir.mkdir(parents=True)

    report = report_dir / "pve01.md"

    report.write_text(
        """# pve01 Infrastructure Report

Generated:
2026-08-15 18:00:00

---

## Health Summary

Status:
Healthy

Failed Services:
0

---

## CPU

Cores:
12

Load:
0.42

---

## Memory

Total:
8192 MB

Used:
45.0%
""",
        encoding="utf-8",
    )

    return root


def configure_service(
    tmp_path,
    monkeypatch,
):
    service = HostReportExportService()
    service.root = make_report(tmp_path)

    class FakeInventory:
        def find_host(self, hostname):
            if hostname == "pve01":
                return {
                    "hostname": hostname,
                    "ip": "192.168.10.10",
                }

            return None

    monkeypatch.setattr(
        service,
        "inventory",
        FakeInventory(),
    )

    return service


def test_txt_returns_existing_host_report(
    tmp_path,
    monkeypatch,
):
    service = configure_service(
        tmp_path,
        monkeypatch,
    )

    result = service.txt("pve01")

    assert result.startswith(
        b"# pve01 Infrastructure Report"
    )
    assert b"Health Summary" in result
    assert b"Status:" in result


def test_csv_returns_structured_host_report(
    tmp_path,
    monkeypatch,
):
    service = configure_service(
        tmp_path,
        monkeypatch,
    )

    result = service.csv("pve01").decode(
        "utf-8"
    )

    assert (
        "hostname,section,metric,value"
        in result
    )

    assert (
        "pve01,Health Summary,Status,Healthy"
        in result
    )

    assert (
        "pve01,CPU,Cores,12"
        in result
    )


def test_pdf_returns_pdf_bytes(
    tmp_path,
    monkeypatch,
):
    service = configure_service(
        tmp_path,
        monkeypatch,
    )

    result = service.pdf("pve01")

    assert result.startswith(
        b"%PDF-"
    )
    assert len(result) > 100


def test_missing_host_is_rejected(
    tmp_path,
    monkeypatch,
):
    service = configure_service(
        tmp_path,
        monkeypatch,
    )

    try:
        service.txt("missing")
    except ValueError as exc:
        assert str(exc) == (
            "Inventory host not found: missing"
        )
    else:
        raise AssertionError(
            "Expected ValueError"
        )


def test_missing_report_is_rejected(
    tmp_path,
    monkeypatch,
):
    service = configure_service(
        tmp_path,
        monkeypatch,
    )

    service.inventory.find_host = (
        lambda hostname: {
            "hostname": hostname,
        }
    )

    try:
        service.txt("pve02")
    except FileNotFoundError as exc:
        assert str(exc) == (
            "Host report not found: pve02"
        )
    else:
        raise AssertionError(
            "Expected FileNotFoundError"
        )


def test_export_prefers_canonical_markdown_and_can_read_unverified_fallback(tmp_path, monkeypatch):
    service = configure_service(tmp_path, monkeypatch)
    parent = service.root / "current" / "cmdb"
    fallback = parent / "unverified"
    fallback.mkdir()
    (fallback / "pve01.md").write_text("# Unverified output")
    assert service.txt("pve01").startswith(b"# pve01 Infrastructure Report")
    (parent / "pve01.md").unlink()
    assert service.txt("pve01") == b"# Unverified output"


def test_rebuild_rejects_previous_current_exports_and_retains_history(tmp_path, monkeypatch):
    import json

    import pytest

    from himp.database.host_identity import HostIdentityRepository
    from himp.models.dashboard import Dashboard

    monkeypatch.setenv("HIMP_DATABASE_PATH", str(tmp_path / "fixture.db"))
    service = HostReportExportService()
    service.root = tmp_path / "reports"
    service.inventory.save_host({
        "hostname": "fixture", "group": "test", "ip": "192.0.2.1", "user": "fixture", "become": False,
    })
    identities = HostIdentityRepository(service.inventory)
    identities.backfill()
    current = identities.report_bindings()["fixture"]
    host_id = current["host_id"]
    report = f"<!-- himp-host-identity: {json.dumps(current)} -->\n# Previous installation\n"
    canonical = service.root / "current" / "cmdb" / "fixture.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_text(report)
    history = service.root / "history" / "cmdb" / host_id / "1" / "report.md"
    history.parent.mkdir(parents=True)
    history.write_text(report)
    cache = tmp_path / "dashboard.json"
    cache.write_text(json.dumps({"generated": "fixture", "hosts": [{
        "hostname": "fixture", "ip": "192.0.2.1", "os": "fixture", "kernel": "fixture",
        "score": 100, "status": "HEALTHY", "host_identity": current,
    }]}))
    assert service.txt("fixture") == b"# Previous installation\n"
    assert len(Dashboard.load(cache, bindings=identities.report_bindings()).hosts) == 1
    assert identities.record_rebuild(host_id, 1) == 2
    for export in (service.txt, service.csv, service.pdf):
        with pytest.raises(FileNotFoundError, match="Host report not found"):
            export("fixture")
    assert Dashboard.load(cache, bindings=identities.report_bindings()).hosts == []
    assert "Previous installation" in service.history("fixture", 1)
