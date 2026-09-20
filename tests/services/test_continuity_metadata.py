import pytest
import yaml

from himp.services.continuity_metadata import (
    ContinuityMetadataService,
)


def write_config(
    path,
    entities,
):
    path.write_text(
        yaml.safe_dump(
            {
                "entities": entities,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def valid_entry():
    return {
        "entity_type": "application",
        "entity_id": "himp",
        "display_name": "HIMP",
        "continuity_role": "management",
        "criticality": "important",
        "household_impact": (
            "Management visibility may be unavailable."
        ),
        "recovery_authority": "technical_only",
        "can_wait": (
            "Usually, if essential household services "
            "are still working."
        ),
    }


def test_loads_production_continuity_catalog():
    service = ContinuityMetadataService(
        "config/continuity_metadata.yml"
    )

    metadata = service.load()

    assert set(metadata) == {
        (
            "application",
            "himp",
        ),
        (
            "database",
            "himp",
        ),
        (
            "host",
            "automation.server.arpa",
        ),
        (
            "host",
            "himpdb01.server.arpa",
        ),
        (
            "host",
            "freepbx",
        ),
        (
            "service",
            "home_telephone",
        ),
    }

    assert {
        key: item["criticality"]
        for key, item in metadata.items()
    } == {
        (
            "application",
            "himp",
        ): "important",
        (
            "database",
            "himp",
        ): "important",
        (
            "host",
            "automation.server.arpa",
        ): "important",
        (
            "host",
            "himpdb01.server.arpa",
        ): "important",
        (
            "host",
            "freepbx",
        ): "critical",
        (
            "service",
            "home_telephone",
        ): "critical",
    }

    assert all(
        item["recovery_authority"]
        == "technical_only"
        for item in metadata.values()
    )


def test_loads_valid_metadata(
    tmp_path,
):
    path = tmp_path / "continuity.yml"

    write_config(
        path,
        [
            valid_entry(),
        ],
    )

    service = ContinuityMetadataService(
        path
    )

    result = service.load()

    assert (
        result[
            (
                "application",
                "himp",
            )
        ]["display_name"]
        == "HIMP"
    )


def test_get_returns_entity_metadata(
    tmp_path,
):
    path = tmp_path / "continuity.yml"

    write_config(
        path,
        [
            valid_entry(),
        ],
    )

    service = ContinuityMetadataService(
        path
    )

    result = service.get(
        " Application ",
        " himp ",
    )

    assert result["entity_id"] == "himp"
    assert result["criticality"] == "important"


def test_get_returns_none_for_unknown_entity(
    tmp_path,
):
    path = tmp_path / "continuity.yml"

    write_config(
        path,
        [
            valid_entry(),
        ],
    )

    service = ContinuityMetadataService(
        path
    )

    assert (
        service.get(
            "host",
            "unknown",
        )
        is None
    )


@pytest.mark.parametrize(
    "field",
    [
        "entity_type",
        "entity_id",
        "display_name",
        "continuity_role",
        "criticality",
        "household_impact",
        "recovery_authority",
        "can_wait",
    ],
)
def test_rejects_missing_required_field(
    tmp_path,
    field,
):
    path = tmp_path / "continuity.yml"

    entry = valid_entry()
    del entry[field]

    write_config(
        path,
        [
            entry,
        ],
    )

    service = ContinuityMetadataService(
        path
    )

    with pytest.raises(
        ValueError,
        match="missing fields",
    ):
        service.load()


@pytest.mark.parametrize(
    "field",
    [
        "entity_type",
        "entity_id",
        "display_name",
        "continuity_role",
        "criticality",
        "household_impact",
        "recovery_authority",
        "can_wait",
    ],
)
def test_rejects_empty_required_field(
    tmp_path,
    field,
):
    path = tmp_path / "continuity.yml"

    entry = valid_entry()
    entry[field] = "   "

    write_config(
        path,
        [
            entry,
        ],
    )

    service = ContinuityMetadataService(
        path
    )

    with pytest.raises(
        ValueError,
        match=field,
    ):
        service.load()


def test_rejects_unknown_entity_type(
    tmp_path,
):
    path = tmp_path / "continuity.yml"

    entry = valid_entry()
    entry["entity_type"] = "banana"

    write_config(
        path,
        [
            entry,
        ],
    )

    service = ContinuityMetadataService(
        path
    )

    with pytest.raises(
        ValueError,
        match="unsupported entity_type",
    ):
        service.load()


def test_rejects_unknown_criticality(
    tmp_path,
):
    path = tmp_path / "continuity.yml"

    entry = valid_entry()
    entry["criticality"] = "catastrophic"

    write_config(
        path,
        [
            entry,
        ],
    )

    service = ContinuityMetadataService(
        path
    )

    with pytest.raises(
        ValueError,
        match="unsupported criticality",
    ):
        service.load()


def test_rejects_unknown_recovery_authority(
    tmp_path,
):
    path = tmp_path / "continuity.yml"

    entry = valid_entry()
    entry["recovery_authority"] = "anyone"

    write_config(
        path,
        [
            entry,
        ],
    )

    service = ContinuityMetadataService(
        path
    )

    with pytest.raises(
        ValueError,
        match="unsupported recovery_authority",
    ):
        service.load()


def test_rejects_duplicate_entity(
    tmp_path,
):
    path = tmp_path / "continuity.yml"

    entry = valid_entry()

    write_config(
        path,
        [
            entry,
            entry,
        ],
    )

    service = ContinuityMetadataService(
        path
    )

    with pytest.raises(
        ValueError,
        match="Duplicate continuity metadata",
    ):
        service.load()


def test_rejects_non_mapping_configuration(
    tmp_path,
):
    path = tmp_path / "continuity.yml"

    path.write_text(
        "- invalid\n",
        encoding="utf-8",
    )

    service = ContinuityMetadataService(
        path
    )

    with pytest.raises(
        ValueError,
        match="must be a mapping",
    ):
        service.load()


def test_rejects_non_list_entities(
    tmp_path,
):
    path = tmp_path / "continuity.yml"

    path.write_text(
        "entities: invalid\n",
        encoding="utf-8",
    )

    service = ContinuityMetadataService(
        path
    )

    with pytest.raises(
        ValueError,
        match="entities must be a list",
    ):
        service.load()


@pytest.mark.parametrize(
    (
        "entity_type",
        "entity_id",
        "message",
    ),
    [
        ("", "himp", "entity_type"),
        ("application", "", "entity_id"),
    ],
)
def test_get_rejects_empty_identity(
    tmp_path,
    entity_type,
    entity_id,
    message,
):
    path = tmp_path / "continuity.yml"

    write_config(
        path,
        [
            valid_entry(),
        ],
    )

    service = ContinuityMetadataService(
        path
    )

    with pytest.raises(
        ValueError,
        match=message,
    ):
        service.get(
            entity_type,
            entity_id,
        )


def test_production_home_telephone_continuity_metadata():
    service = ContinuityMetadataService(
        "config/continuity_metadata.yml"
    )

    metadata = service.load()

    telephone = metadata[
        (
            "service",
            "home_telephone",
        )
    ]

    freepbx = metadata[
        (
            "host",
            "freepbx",
        )
    ]

    assert (
        telephone["display_name"]
        == "Home Telephone"
    )

    assert (
        telephone["continuity_role"]
        == "essential_household_service"
    )

    assert telephone["criticality"] == "critical"

    assert (
        telephone["recovery_authority"]
        == "technical_only"
    )

    assert (
        freepbx["display_name"]
        == "Home Telephone Server"
    )

    assert (
        freepbx["continuity_role"]
        == "essential_service_infrastructure"
    )

    assert freepbx["criticality"] == "critical"

    assert (
        freepbx["recovery_authority"]
        == "technical_only"
    )
