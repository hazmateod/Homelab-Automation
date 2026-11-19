from himp.services.reports import ReportService


def test_operational_summary_exposes_dashboard_and_report_inventory(
    tmp_path,
    monkeypatch,
):
    service = ReportService()

    service.root = tmp_path / "reports"

    dashboard_dir = service.root / "dashboard"
    current_dir = service.root / "current"
    history_dir = service.root / "history"
    health_dir = service.root / "health"
    discovery_dir = service.root / "discovery"
    json_dir = service.root / "json"

    dashboard_dir.mkdir(parents=True)
    current_dir.mkdir()
    history_dir.mkdir()
    health_dir.mkdir()
    discovery_dir.mkdir()
    json_dir.mkdir()

    (dashboard_dir / "dashboard.json").write_text("{}")
    (current_dir / "host1.md").write_text("current")
    (current_dir / "host2.md").write_text("current")
    (history_dir / "host1.md").write_text("history")
    (health_dir / "health.json").write_text("{}")
    (discovery_dir / "discovery.json").write_text("{}")
    (json_dir / "host1.json").write_text("{}")

    monkeypatch.setattr(
        service,
        "dashboard",
        lambda: {
            "generated": "2026-08-15T13:43:41Z",
            "hosts": 43,
            "healthy": 3,
            "warnings": 0,
            "critical": 1,
            "unknown": 39,
            "average_score": 25.0,
        },
    )

    service.automation_executions = (
        FakeAutomationExecutionRepository()
    )

    assert service.operational_summary() == {
        "generated": "2026-08-15T13:43:41Z",
        "dashboard": {
            "hosts": 43,
            "healthy": 3,
            "warnings": 0,
            "critical": 1,
            "unknown": 39,
            "average_score": 25.0,
        },
        "reports": {
            "current": 2,
            "history": 1,
            "health": 1,
            "discovery": 1,
            "json": 1,
        },
        "executions": {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "recent": [],
        },
    }


def test_operational_summary_handles_missing_dashboard():
    service = ReportService()

    service.root = service.root / "missing-phase-9-2-test"

    service.automation_executions = (
        FakeAutomationExecutionRepository()
    )

    assert service.operational_summary() == {
        "generated": None,
        "dashboard": None,
        "reports": {
            "current": 0,
            "history": 0,
            "health": 0,
            "discovery": 0,
            "json": 0,
        },
        "executions": {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "recent": [],
        },
    }


class FakeAutomationExecutionRepository:
    def __init__(self, history=None):
        self._history = history or []

    def history(self, limit=50):
        return self._history[:limit]


def test_operational_summary_includes_execution_history(
    tmp_path,
    monkeypatch,
):
    service = ReportService()

    service.root = tmp_path / "reports"

    monkeypatch.setattr(
        service,
        "dashboard",
        lambda: None,
    )

    service.automation_executions = (
        FakeAutomationExecutionRepository(
            [
                {
                    "id": 3,
                    "task_id": "scheduled_updates",
                    "success": True,
                    "elapsed": 12.5,
                    "result": {
                        "changed": 4,
                    },
                    "executed_at": "2026-08-15 14:00:00",
                },
                {
                    "id": 2,
                    "task_id": "generate_reports",
                    "success": False,
                    "elapsed": 4.25,
                    "result": {
                        "error": "timeout",
                    },
                    "executed_at": "2026-08-15 13:00:00",
                },
            ]
        )
    )

    result = service.operational_summary()

    assert result["executions"] == {
        "total": 2,
        "successful": 1,
        "failed": 1,
        "recent": [
            {
                "id": 3,
                "task_id": "scheduled_updates",
                "success": True,
                "elapsed": 12.5,
                "executed_at": "2026-08-15 14:00:00",
            },
            {
                "id": 2,
                "task_id": "generate_reports",
                "success": False,
                "elapsed": 4.25,
                "executed_at": "2026-08-15 13:00:00",
            },
        ],
    }


def test_operational_summary_handles_no_execution_history(
    tmp_path,
    monkeypatch,
):
    service = ReportService()

    service.root = tmp_path / "reports"

    monkeypatch.setattr(
        service,
        "dashboard",
        lambda: None,
    )

    service.automation_executions = (
        FakeAutomationExecutionRepository()
    )

    result = service.operational_summary()

    assert result["executions"] == {
        "total": 0,
        "successful": 0,
        "failed": 0,
        "recent": [],
    }


def test_dashboard_entry_points_send_selected_reports_to_ansible(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from himp.commands import dashboard
    from himp.database.inventory import InventoryRepository
    from himp.services import update

    monkeypatch.setenv("HIMP_DATABASE_PATH", str(tmp_path / "inventory.db"))
    repository = InventoryRepository()
    repository.save_host({
        "hostname": "retired", "group": "test", "ip": "192.0.2.1", "user": "fixture", "become": False,
    })
    repository.mark_removed("retired")
    calls = []

    def runner(playbook, **options):
        calls.append((playbook, options))
        return SimpleNamespace(success=True, return_code=0, elapsed=0)

    monkeypatch.setattr(dashboard, "run_playbook", runner)
    monkeypatch.setattr(dashboard, "log", lambda *args: None)
    monkeypatch.setattr(update, "run_playbook", runner)
    dashboard.run(None)
    assert update.UpdateService._refresh_dashboard("snapshot.yml", 10)["status"] == "succeeded"
    assert len(calls) == 2
    assert all(options["extra_vars"] == {"himp_dashboard_reports": [], "himp_dashboard_skipped_reports": []} for _, options in calls)


def test_dashboard_refresh_and_exports_preserve_verified_alias_and_isolate_bad_reports(tmp_path, monkeypatch):
    import json
    import shutil
    from pathlib import Path

    import pytest

    from himp.database.host_identity import HostIdentityRepository
    from himp.database.inventory import InventoryRepository
    from himp.lib.ansible import run_playbook
    from himp.services.host_report_export import HostReportExportService

    if shutil.which("ansible-playbook") is None:
        pytest.skip("ansible-core is required for the dashboard fixture")

    monkeypatch.setenv("HIMP_DATABASE_PATH", str(tmp_path / "fixture.db"))
    root = tmp_path / "reports"
    json_dir = root / "json"
    json_dir.mkdir(parents=True)
    markdown_dir = root / "current" / "cmdb"
    markdown_dir.mkdir(parents=True)
    repository = InventoryRepository()
    repository.save_host({
        "hostname": "old-name", "group": "test", "ip": "192.0.2.1", "user": "fixture", "become": False,
    })
    identities = HostIdentityRepository(repository)
    identities.backfill()
    binding = identities.report_bindings()["old-name"]
    (json_dir / "old-name.json").write_text(json.dumps({
        "metadata": {"hostname": "old-name", "operating_system": 'OS "quoted"'},
        "host_identity": binding,
        "health": {"overall": {"score": 90, "status": "HEALTHY"}},
    }))
    (markdown_dir / "old-name.md").write_text(
        f"<!-- himp-host-identity: {json.dumps(binding)} -->\n# old-name Infrastructure Report\n"
    )
    (json_dir / "broken.json").write_text("{broken")
    (json_dir / "bad-shape.json").write_text('{"metadata": []}')
    (json_dir / "too-deep.json").write_text("[" * 30_000 + "0")
    identities.rename(repository.find_host("old-name")["id"], "old-name", "new-name", "rename")

    reports = ReportService()
    reports.root = root
    variables = reports.dashboard_variables()
    assert variables["himp_dashboard_skipped_reports"] == ["bad-shape.json", "broken.json", "too-deep.json"]

    repo = Path(__file__).resolve().parents[2]
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    playbook = playbooks / "dashboard.yml"
    shutil.copyfile(repo / "playbooks" / playbook.name, playbook)
    monkeypatch.setenv("ANSIBLE_ROLES_PATH", str(repo / "roles"))
    inventory = tmp_path / "inventory.yml"
    inventory.write_text(
        "all:\n  hosts:\n    localhost: {ansible_connection: local}\n"
        "    new-name: {}\n    broken: {}\n    bad-shape: {}\n"
    )
    result = run_playbook(str(playbook), timeout=25, inventory_path=inventory, extra_vars=variables)
    assert result.success, result.stdout + result.stderr
    assert "broken.json" in result.stdout
    dashboard_json = json.loads((root / "dashboard" / "dashboard.json").read_text())
    assert [host["hostname"] for host in dashboard_json["hosts"]] == ["new-name"]
    assert dashboard_json["skipped_reports"] == ["bad-shape.json", "broken.json", "too-deep.json"]
    assert reports.dashboard()["skipped_reports"] == dashboard_json["skipped_reports"]
    assert dashboard_json["hosts"][0]["os"] == 'OS "quoted"'
    assert "/api/reports/host/new-name/txt" in (root / "dashboard" / "index.html").read_text()
    assert (json_dir / "broken.json").read_text() == "{broken"

    export = HostReportExportService()
    export.root = root
    assert export.txt("new-name").startswith(b"# new-name Infrastructure Report")
    assert export.csv("new-name").startswith(b"hostname,")
    assert export.pdf("new-name").startswith(b"%PDF")
    assert identities.record_rebuild(binding["host_id"], 1) == 2
    assert reports.dashboard_variables()["himp_dashboard_reports"] == []
    with pytest.raises(FileNotFoundError):
        export.txt("new-name")

    # Exercise the dashboard renderer with a payload above Linux's single-argument limit.
    hosts = [f"fixture-{index:04d}" for index in range(700)]
    legacy_report = json.dumps({
        "metadata": {"operating_system": "fixture", "kernel": "fixture"},
        "network": {"primary_ip": "192.0.2.1"},
        "health": {"overall": {"score": 80, "status": "HEALTHY"}},
    })
    for hostname in hosts:
        (json_dir / f"{hostname}.json").write_text(legacy_report)
    inventory.write_text(
        "all:\n  hosts:\n    localhost: {ansible_connection: local}\n"
        + "".join(f"    {hostname}: {{}}\n" for hostname in hosts)
    )
    variables = reports.dashboard_variables()
    assert len(json.dumps(variables).encode()) > 131_072
    result = run_playbook(str(playbook), timeout=45, inventory_path=inventory, extra_vars=variables)
    assert result.success, result.stdout + result.stderr
    dashboard_json = json.loads((root / "dashboard" / "dashboard.json").read_text())
    assert [row["hostname"] for row in dashboard_json["hosts"]] == hosts
    assert "too-deep.json" in dashboard_json["skipped_reports"]
