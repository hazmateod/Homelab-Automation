from himp.services.settings import SettingsService


def test_summary_returns_expected_sections():
    service = SettingsService()

    result = service.summary()

    assert result == {
        "application": {
            "name": "HIMP",
            "version": "1.0.0",
        },
        "system": service.system(),
        "paths": service.paths(),
        "configuration": service.configuration(),
    }


def test_system_returns_runtime_information():
    service = SettingsService()

    result = service.system()

    assert set(result) == {
        "hostname",
        "platform",
        "python",
    }

    assert result["hostname"]
    assert result["platform"]
    assert result["python"]


def test_paths_returns_configured_paths_and_existence():
    service = SettingsService()

    result = service.paths()

    assert result == {
        "inventory": {
            "path": "inventory/hosts.yml",
            "exists": True,
        },
        "dashboard": {
            "path": "reports/dashboard/dashboard.json",
            "exists": True,
        },
        "maintenance_playbook": {
            "path": "playbooks/maintenance.yml",
            "exists": True,
        },
        "report_playbook": {
            "path": "playbooks/generate_reports.yml",
            "exists": True,
        },
        "dashboard_playbook": {
            "path": "playbooks/dashboard.yml",
            "exists": True,
        },
    }


def test_configuration_returns_configured_paths():
    service = SettingsService()

    result = service.configuration()

    assert result == {
        "inventory": "inventory/hosts.yml",
        "dashboard": "reports/dashboard/dashboard.json",
        "maintenance_playbook": "playbooks/maintenance.yml",
        "report_playbook": "playbooks/generate_reports.yml",
        "dashboard_playbook": "playbooks/dashboard.yml",
    }


def test_exists_reports_existing_and_missing_paths(tmp_path):
    service = SettingsService()

    existing = tmp_path / "existing.txt"
    existing.write_text("test")

    assert service.exists(str(existing)) == {
        "path": str(existing),
        "exists": True,
    }

    missing = tmp_path / "missing.txt"

    assert service.exists(str(missing)) == {
        "path": str(missing),
        "exists": False,
    }
