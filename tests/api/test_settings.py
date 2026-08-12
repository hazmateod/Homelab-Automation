import json

from himp.api import server


class FakeSettingsService:
    def summary(self):
        return {
            "application": {
                "name": "HIMP",
                "version": "1.0.0",
            },
            "system": {
                "hostname": "test-host",
                "platform": "test-platform",
                "python": "3.13.5",
            },
            "paths": {
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
            },
            "configuration": {
                "inventory": "inventory/hosts.yml",
                "dashboard": "reports/dashboard/dashboard.json",
                "maintenance_playbook": "playbooks/maintenance.yml",
                "report_playbook": "playbooks/generate_reports.yml",
                "dashboard_playbook": "playbooks/dashboard.yml",
            },
        }


def test_settings_api_returns_settings_summary(
    monkeypatch,
):
    monkeypatch.setattr(
        server.himp,
        "settings",
        FakeSettingsService(),
    )

    response = server.settings_api()

    assert response.status_code == 200
    assert response.media_type == "application/json"
    assert json.loads(
        response.body.decode("utf-8")
    ) == FakeSettingsService().summary()
