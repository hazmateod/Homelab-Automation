import pytest

from himp.config import Config


def make_config(tmp_path):
    return Config(
        inventory=str(tmp_path / "inventory.yml"),
        dashboard=str(tmp_path / "dashboard.json"),
        maintenance_playbook=str(
            tmp_path / "maintenance.yml"
        ),
        report_playbook=str(
            tmp_path / "reports.yml"
        ),
        dashboard_playbook=str(
            tmp_path / "dashboard.yml"
        ),
    )


def test_config_validate_accepts_all_required_paths(tmp_path):
    config = make_config(tmp_path)

    for filename in (
        config.inventory,
        config.dashboard,
        config.maintenance_playbook,
        config.report_playbook,
        config.dashboard_playbook,
    ):
        (tmp_path / filename.split("/")[-1]).touch()

    config.validate()


@pytest.mark.parametrize(
    "missing_field",
    [
        "inventory",
        "dashboard",
        "maintenance_playbook",
        "report_playbook",
        "dashboard_playbook",
    ],
)
def test_config_validate_rejects_missing_required_path(
    tmp_path,
    missing_field,
):
    config = make_config(tmp_path)

    for filename in (
        config.inventory,
        config.dashboard,
        config.maintenance_playbook,
        config.report_playbook,
        config.dashboard_playbook,
    ):
        (tmp_path / filename.split("/")[-1]).touch()

    missing_path = getattr(config, missing_field)
    (tmp_path / missing_path.split("/")[-1]).unlink()

    with pytest.raises(
        FileNotFoundError,
        match=missing_path,
    ):
        config.validate()


def test_config_validate_checks_required_paths_in_order(tmp_path):
    config = make_config(tmp_path)

    with pytest.raises(
        FileNotFoundError,
        match=config.inventory,
    ):
        config.validate()
