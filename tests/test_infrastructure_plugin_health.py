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


def test_generic_role_uses_only_applicable_health_points():
    source = HEALTH.read_text()

    initialization = source.split(
        "- name: Initialize infrastructure health",
        1,
    )[1].split(
        "- name: Add host connectivity",
        1,
    )[0]

    assert "possible: 4" in initialization


def test_required_service_adds_four_possible_points():
    source = HEALTH.read_text()

    task = source.split(
        "- name: Add required service possible health",
        1,
    )[1].split(
        "- name: Check required service",
        1,
    )[0]

    assert "infrastructure_health.possible + 4" in task
    assert "required_service is defined" in task


def test_final_status_uses_applicable_possible_score():
    source = HEALTH.read_text()

    final_scoring = source.split(
        "- name: Calculate infrastructure status",
        1,
    )[1].split(
        "- name: Store infrastructure health",
        1,
    )[0]

    assert (
        ">= infrastructure_health.possible"
        in final_scoring
    )
    assert "earned >= 8" not in final_scoring


def test_failed_required_service_keeps_service_points_possible():
    source = HEALTH.read_text()

    possible_task = source.split(
        "- name: Add required service possible health",
        1,
    )[1].split(
        "- name: Check required service",
        1,
    )[0]

    earned_task = source.split(
        "- name: Add required service health",
        1,
    )[1].split(
        "- name: Add service issue",
        1,
    )[0]

    assert "infrastructure_health.possible + 4" in possible_task
    assert "required_service is defined" in possible_task
    assert "infrastructure_health.earned + 4" in earned_task
