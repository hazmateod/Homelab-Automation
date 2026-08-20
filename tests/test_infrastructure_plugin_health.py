from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DISCOVERY = (
    PROJECT_ROOT
    / "plugins"
    / "infrastructure"
    / "tasks"
    / "discovery.yml"
)

HEALTH = (
    PROJECT_ROOT
    / "plugins"
    / "infrastructure"
    / "tasks"
    / "health.yml"
)


def test_himpdb01_uses_postgres_infrastructure_role():
    source = DISCOVERY.read_text()

    assert "'postgres'" in source
    assert "'himpdb01.server.arpa'" in source
    assert "if inventory_hostname in [" in source


def test_generic_infrastructure_role_remains_supported():
    source = DISCOVERY.read_text()

    assert "'generic'" in source


def test_service_health_requires_required_service():
    source = HEALTH.read_text()

    task = source.split(
        "- name: Add required service health",
        1,
    )[1].split(
        "- name: Add service issue",
        1,
    )[0]

    assert "required_service is defined" in task


def test_service_health_guards_required_process_rc():
    source = HEALTH.read_text()

    assert "required_process.rc is defined" in source

    service_health = source.split(
        "- name: Add required service health",
        1,
    )[1].split(
        "- name: Add service issue",
        1,
    )[0]

    service_issue = source.split(
        "- name: Add service issue",
        1,
    )[1].split(
        "Final scoring",
        1,
    )[0]

    assert (
        "required_process.rc is defined"
        in service_health
    )

    assert (
        "required_process.rc is defined"
        in service_issue
    )


def test_postgres_role_requires_postgresql_service():
    source = HEALTH.read_text()

    postgres = source.split(
        "- name: Validate postgres service",
        1,
    )[1].split(
        "- name: Validate uptimekuma service",
        1,
    )[0]

    assert (
        "required_service: postgresql.service"
        in postgres
    )

    assert (
        'infrastructure_role == "postgres"'
        in postgres
    )
