import pytest
import yaml

from himp.services.service_availability_policy import (
    ServiceAvailabilityPolicyService,
)


def write_config(
    path,
    services,
):
    path.write_text(
        yaml.safe_dump(
            {
                "services": services,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def valid_policy():
    return {
        "service_type": "service",
        "service_id": "example_service",
        "display_name": "Example Service",
        "minimum_available": 1,
        "providers": [
            {
                "entity_type": "host",
                "entity_id": "provider-a",
            },
            {
                "entity_type": "host",
                "entity_id": "provider-b",
            },
        ],
    }


def test_loads_valid_policy(
    tmp_path,
):
    path = tmp_path / "availability.yml"

    write_config(
        path,
        [
            valid_policy(),
        ],
    )

    service = (
        ServiceAvailabilityPolicyService(
            path
        )
    )

    result = service.load()

    policy = result[
        (
            "service",
            "example_service",
        )
    ]

    assert (
        policy["display_name"]
        == "Example Service"
    )

    assert policy["minimum_available"] == 1

    assert policy["providers"] == [
        {
            "entity_type": "host",
            "entity_id": "provider-a",
        },
        {
            "entity_type": "host",
            "entity_id": "provider-b",
        },
    ]


def test_get_normalizes_service_identity(
    tmp_path,
):
    path = tmp_path / "availability.yml"

    write_config(
        path,
        [
            valid_policy(),
        ],
    )

    service = (
        ServiceAvailabilityPolicyService(
            path
        )
    )

    result = service.get(
        " Service ",
        " example_service ",
    )

    assert result is not None
    assert result["service_id"] == "example_service"


def test_get_returns_none_for_unknown_service(
    tmp_path,
):
    path = tmp_path / "availability.yml"

    write_config(
        path,
        [
            valid_policy(),
        ],
    )

    service = (
        ServiceAvailabilityPolicyService(
            path
        )
    )

    assert (
        service.get(
            "service",
            "unknown",
        )
        is None
    )


@pytest.mark.parametrize(
    "field",
    [
        "service_type",
        "service_id",
        "display_name",
        "minimum_available",
        "providers",
    ],
)
def test_rejects_missing_policy_field(
    tmp_path,
    field,
):
    path = tmp_path / "availability.yml"

    policy = valid_policy()
    del policy[field]

    write_config(
        path,
        [
            policy,
        ],
    )

    service = (
        ServiceAvailabilityPolicyService(
            path
        )
    )

    with pytest.raises(
        ValueError,
        match="missing fields",
    ):
        service.load()


@pytest.mark.parametrize(
    (
        "field",
        "value",
    ),
    [
        ("service_type", ""),
        ("service_id", ""),
        ("display_name", ""),
    ],
)
def test_rejects_empty_policy_text(
    tmp_path,
    field,
    value,
):
    path = tmp_path / "availability.yml"

    policy = valid_policy()
    policy[field] = value

    write_config(
        path,
        [
            policy,
        ],
    )

    service = (
        ServiceAvailabilityPolicyService(
            path
        )
    )

    with pytest.raises(
        ValueError,
        match=field,
    ):
        service.load()


def test_rejects_unknown_service_type(
    tmp_path,
):
    path = tmp_path / "availability.yml"

    policy = valid_policy()
    policy["service_type"] = "banana"

    write_config(
        path,
        [
            policy,
        ],
    )

    service = (
        ServiceAvailabilityPolicyService(
            path
        )
    )

    with pytest.raises(
        ValueError,
        match="Unsupported service_type",
    ):
        service.load()


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        True,
        "1",
    ],
)
def test_rejects_invalid_minimum_available(
    tmp_path,
    value,
):
    path = tmp_path / "availability.yml"

    policy = valid_policy()
    policy["minimum_available"] = value

    write_config(
        path,
        [
            policy,
        ],
    )

    service = (
        ServiceAvailabilityPolicyService(
            path
        )
    )

    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        service.load()


def test_rejects_empty_provider_list(
    tmp_path,
):
    path = tmp_path / "availability.yml"

    policy = valid_policy()
    policy["providers"] = []

    write_config(
        path,
        [
            policy,
        ],
    )

    service = (
        ServiceAvailabilityPolicyService(
            path
        )
    )

    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        service.load()


def test_rejects_minimum_above_provider_count(
    tmp_path,
):
    path = tmp_path / "availability.yml"

    policy = valid_policy()
    policy["minimum_available"] = 3

    write_config(
        path,
        [
            policy,
        ],
    )

    service = (
        ServiceAvailabilityPolicyService(
            path
        )
    )

    with pytest.raises(
        ValueError,
        match="cannot exceed provider count",
    ):
        service.load()


def test_rejects_duplicate_provider(
    tmp_path,
):
    path = tmp_path / "availability.yml"

    policy = valid_policy()

    policy["providers"].append(
        {
            "entity_type": "host",
            "entity_id": "provider-a",
        }
    )

    write_config(
        path,
        [
            policy,
        ],
    )

    service = (
        ServiceAvailabilityPolicyService(
            path
        )
    )

    with pytest.raises(
        ValueError,
        match="Duplicate service availability provider",
    ):
        service.load()


def test_rejects_duplicate_service_policy(
    tmp_path,
):
    path = tmp_path / "availability.yml"

    policy = valid_policy()

    write_config(
        path,
        [
            policy,
            policy,
        ],
    )

    service = (
        ServiceAvailabilityPolicyService(
            path
        )
    )

    with pytest.raises(
        ValueError,
        match="Duplicate service availability policy",
    ):
        service.load()


def test_rejects_unknown_provider_entity_type(
    tmp_path,
):
    path = tmp_path / "availability.yml"

    policy = valid_policy()

    policy["providers"][0][
        "entity_type"
    ] = "banana"

    write_config(
        path,
        [
            policy,
        ],
    )

    service = (
        ServiceAvailabilityPolicyService(
            path
        )
    )

    with pytest.raises(
        ValueError,
        match="Unsupported provider entity_type",
    ):
        service.load()


def test_rejects_duplicate_provider_after_normalization(
    tmp_path,
):
    path = tmp_path / "availability.yml"

    policy = valid_policy()

    policy["providers"].append(
        {
            "entity_type": " Host ",
            "entity_id": "provider-a",
        }
    )

    write_config(
        path,
        [
            policy,
        ],
    )

    service = (
        ServiceAvailabilityPolicyService(
            path
        )
    )

    with pytest.raises(
        ValueError,
        match="Duplicate service availability provider",
    ):
        service.load()


def test_rejects_non_mapping_configuration(
    tmp_path,
):
    path = tmp_path / "availability.yml"

    path.write_text(
        "- invalid\n",
        encoding="utf-8",
    )

    service = (
        ServiceAvailabilityPolicyService(
            path
        )
    )

    with pytest.raises(
        ValueError,
        match="must be a mapping",
    ):
        service.load()


def test_rejects_non_list_services(
    tmp_path,
):
    path = tmp_path / "availability.yml"

    path.write_text(
        "services: invalid\n",
        encoding="utf-8",
    )

    service = (
        ServiceAvailabilityPolicyService(
            path
        )
    )

    with pytest.raises(
        ValueError,
        match="services must be a list",
    ):
        service.load()


def test_rejects_non_mapping_provider(
    tmp_path,
):
    path = tmp_path / "availability.yml"

    policy = valid_policy()
    policy["providers"][0] = "provider-a"

    write_config(
        path,
        [
            policy,
        ],
    )

    service = (
        ServiceAvailabilityPolicyService(
            path
        )
    )

    with pytest.raises(
        ValueError,
        match="provider must be a mapping",
    ):
        service.load()


def test_rejects_unexpected_policy_field(
    tmp_path,
):
    path = tmp_path / "availability.yml"

    policy = valid_policy()
    policy["invented"] = "value"

    write_config(
        path,
        [
            policy,
        ],
    )

    service = (
        ServiceAvailabilityPolicyService(
            path
        )
    )

    with pytest.raises(
        ValueError,
        match="unsupported fields",
    ):
        service.load()


def test_rejects_unexpected_provider_field(
    tmp_path,
):
    path = tmp_path / "availability.yml"

    policy = valid_policy()
    policy["providers"][0][
        "invented"
    ] = "value"

    write_config(
        path,
        [
            policy,
        ],
    )

    service = (
        ServiceAvailabilityPolicyService(
            path
        )
    )

    with pytest.raises(
        ValueError,
        match="unsupported fields",
    ):
        service.load()


def test_loads_production_service_availability_catalog():
    service = ServiceAvailabilityPolicyService(
        "config/service_availability.yml"
    )

    policies = service.load()

    assert set(policies) == {
        (
            "service",
            "home_telephone",
        ),
    }


def test_production_home_telephone_availability_policy():
    service = ServiceAvailabilityPolicyService(
        "config/service_availability.yml"
    )

    policy = service.get(
        "service",
        "home_telephone",
    )

    assert policy is not None

    assert (
        policy["display_name"]
        == "Home Telephone"
    )

    assert policy["minimum_available"] == 1

    assert policy["providers"] == [
        {
            "entity_type": "host",
            "entity_id": "freepbx",
        }
    ]


def test_production_catalog_does_not_model_dns_before_functional_evidence():
    service = ServiceAvailabilityPolicyService(
        "config/service_availability.yml"
    )

    policies = service.load()

    assert (
        "service",
        "home_dns",
    ) not in policies

    provider_ids = {
        provider["entity_id"]
        for policy in policies.values()
        for provider in policy["providers"]
    }

    dns_inventory_hosts = {
        "unbound107",
        "unbound108",
        "unbound37100",
        "unbound37101",
        "unbound1007",
        "unbound1008",
        "dns1009",
        "dns1011",
        "dns1012",
        "dns1013",
        "dns3748",
        "dns3749",
        "dns1070",
        "dns1071",
        "pihole3710",
        "pihole3712",
        "pihole1010",
        "pihole1011",
        "pihole1012",
        "pihole1013",
        "pihole1014",
        "pihole1016",
        "pihole1017",
    }

    assert provider_ids.isdisjoint(
        dns_inventory_hosts
    )


def test_production_availability_services_have_continuity_metadata():
    from himp.services.continuity_metadata import (
        ContinuityMetadataService,
    )

    policies = ServiceAvailabilityPolicyService(
        "config/service_availability.yml"
    ).load()

    continuity = ContinuityMetadataService(
        "config/continuity_metadata.yml"
    ).load()

    for key in policies:
        assert key in continuity


def test_production_availability_providers_have_continuity_metadata():
    from himp.services.continuity_metadata import (
        ContinuityMetadataService,
    )

    policies = ServiceAvailabilityPolicyService(
        "config/service_availability.yml"
    ).load()

    continuity = ContinuityMetadataService(
        "config/continuity_metadata.yml"
    ).load()

    for policy in policies.values():
        for provider in policy["providers"]:
            key = (
                provider["entity_type"],
                provider["entity_id"],
            )

            assert key in continuity


def test_production_availability_host_providers_exist_in_inventory():
    from pathlib import Path

    policies = ServiceAvailabilityPolicyService(
        "config/service_availability.yml"
    ).load()

    inventory = yaml.safe_load(
        Path(
            "inventory/hosts.yml"
        ).read_text(
            encoding="utf-8"
        )
    )

    inventory_hosts = set()

    def collect_hosts(node):
        if not isinstance(node, dict):
            return

        hosts = node.get("hosts")

        if isinstance(hosts, dict):
            inventory_hosts.update(
                str(host).strip()
                for host in hosts
            )

        children = node.get("children")

        if isinstance(children, dict):
            for child in children.values():
                collect_hosts(child)

    collect_hosts(
        inventory.get(
            "all",
            inventory,
        )
    )

    for policy in policies.values():
        for provider in policy["providers"]:
            if (
                provider["entity_type"]
                == "host"
            ):
                assert (
                    provider["entity_id"]
                    in inventory_hosts
                )


def test_production_availability_providers_match_runs_on_topology():
    from pathlib import Path

    policies = ServiceAvailabilityPolicyService(
        "config/service_availability.yml"
    ).load()

    document = yaml.safe_load(
        Path(
            "config/infrastructure_relationships.yml"
        ).read_text(
            encoding="utf-8"
        )
    )

    relationships = {
        (
            item["source_type"].strip().lower(),
            item["source_id"].strip(),
            item["relationship_type"].strip().lower(),
            item["target_type"].strip().lower(),
            item["target_id"].strip(),
        )
        for item in document["relationships"]
    }

    for policy in policies.values():
        for provider in policy["providers"]:
            expected = (
                policy["service_type"],
                policy["service_id"],
                "runs_on",
                provider["entity_type"],
                provider["entity_id"],
            )

            assert expected in relationships
