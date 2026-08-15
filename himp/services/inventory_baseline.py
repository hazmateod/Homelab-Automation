"""
Inventory Baseline Service.

Compares current inventory against a named deterministic baseline.
"""

class InventoryBaselineService:
    """
    Compares current inventory configuration against a baseline.
    """

    FIELDS = (
        "group",
        "ip",
        "user",
        "become",
    )

    def __init__(
        self,
        inventory,
        repository,
    ):
        self.inventory = inventory
        self.repository = repository

    def compare(
        self,
        name,
    ):
        baseline = self.repository.find(name)

        if baseline is None:
            raise ValueError(
                f"Inventory baseline not found: {name}"
            )

        current_hosts = {
            host["hostname"]: host
            for host in self.inventory.all_hosts()
        }

        baseline_hosts = {
            host["hostname"]: host
            for host in baseline["hosts"]
        }

        drift = []

        for hostname in sorted(
            baseline_hosts.keys() - current_hosts.keys()
        ):
            expected = self._configuration(
                baseline_hosts[hostname]
            )

            drift.append(
                {
                    "hostname": hostname,
                    "field": None,
                    "expected": expected,
                    "actual": None,
                    "drift_type": "REMOVED",
                }
            )

        for hostname in sorted(
            current_hosts.keys() - baseline_hosts.keys()
        ):
            actual = self._configuration(
                current_hosts[hostname]
            )

            drift.append(
                {
                    "hostname": hostname,
                    "field": None,
                    "expected": None,
                    "actual": actual,
                    "drift_type": "ADDED",
                }
            )

        for hostname in sorted(
            baseline_hosts.keys() & current_hosts.keys()
        ):
            expected = baseline_hosts[hostname]
            actual = current_hosts[hostname]

            for field in self.FIELDS:
                expected_value = expected[field]
                actual_value = actual[field]

                if expected_value != actual_value:
                    drift.append(
                        {
                            "hostname": hostname,
                            "field": field,
                            "expected": expected_value,
                            "actual": actual_value,
                            "drift_type": "CHANGED",
                        }
                    )

        return {
            "baseline": name,
            "drift": drift,
        }

    def _configuration(
        self,
        host,
    ):
        return {
            field: host[field]
            for field in self.FIELDS
        }
