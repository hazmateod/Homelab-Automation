from pathlib import Path

import pytest

from himp.config import Config


def make_config(tmp_path):
    return Config(
        inventory=str(
            tmp_path / "inventory.yml"
        ),
        dashboard=str(
            tmp_path / "dashboard.json"
        ),
        maintenance_playbook=str(
            tmp_path / "maintenance.yml"
        ),
        report_playbook=str(
            tmp_path / "reports.yml"
        ),
        dashboard_playbook=str(
            tmp_path / "dashboard.yml"
        ),
        infrastructure_relationships=str(
            tmp_path
            / "infrastructure_relationships.yml"
        ),
    )


def required_paths(config):
    return [
        config.inventory,
        config.dashboard,
        config.maintenance_playbook,
        config.report_playbook,
        config.dashboard_playbook,
        config.infrastructure_relationships,
    ]


def test_config_validate_accepts_all_required_paths(
    tmp_path,
):
    config = make_config(tmp_path)

    for filename in required_paths(
        config
    ):
        Path(filename).touch()

    config.validate()


@pytest.mark.parametrize(
    "missing_field",
    [
        "inventory",
        "dashboard",
        "maintenance_playbook",
        "report_playbook",
        "dashboard_playbook",
        "infrastructure_relationships",
    ],
)
def test_config_validate_rejects_missing_required_path(
    tmp_path,
    missing_field,
):
    config = make_config(tmp_path)

    for filename in required_paths(
        config
    ):
        Path(filename).touch()

    missing = Path(
        getattr(
            config,
            missing_field,
        )
    )

    missing.unlink()

    with pytest.raises(
        FileNotFoundError
    ) as error:
        config.validate()

    assert (
        str(error.value)
        == str(missing)
    )


def test_config_validate_checks_required_paths_in_order(
    tmp_path,
):
    config = make_config(tmp_path)

    expected = required_paths(
        config
    )

    for filename in expected[1:]:
        Path(filename).touch()

    with pytest.raises(
        FileNotFoundError
    ) as error:
        config.validate()

    assert (
        str(error.value)
        == expected[0]
    )
