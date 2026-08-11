"""
Host Health Service.
"""

from himp.database.host_health import HostHealthRepository
from himp.database.inventory import InventoryRepository
from himp.health.models import (
    HealthCheckResult,
    HealthStatus,
    HostHealthResult,
)
import time

from himp.services.ssh import SSHService


class HostHealthService:
    """
    Provides host-level health checks.
    """

    CHECK_NAME = "ssh"

    def __init__(self):

        self.inventory = InventoryRepository()

        self.repository = HostHealthRepository()

        self.ssh = SSHService()

    def check_host(
        self,
        hostname,
        timeout=None,
    ):
        host = self.inventory.find_host(
            hostname
        )

        if host is None:
            raise ValueError(
                f"Inventory host not found: {hostname}"
            )

        ssh = self.ssh.test(
            hostname=host["hostname"],
            ip=host["ip"],
            user=host["ansible_user"],
            timeout=timeout,
        )

        status = (
            HealthStatus.PASS
            if ssh.success
            else HealthStatus.FAIL
        )

        result = HealthCheckResult(
            plugin="host",
            check=self.CHECK_NAME,
            status=status,
            message=ssh.message,
            duration_ms=round(
                ssh.elapsed * 1000,
                3,
            ),
            details={
                "ip": ssh.ip,
                "user": ssh.user,
                "ssh_status": ssh.status,
                "return_code": ssh.return_code,
                "stdout": ssh.stdout,
                "stderr": ssh.stderr,
            },
        )

        self.repository.save(
            hostname=hostname,
            result=result,
        )

        return HostHealthResult(
            hostname=hostname,
            results=[result],
        )


    def check_hosts(
        self,
        hostnames,
        timeout=None,
    ):
        results = []
        started = time.perf_counter()

        for hostname in hostnames:

            remaining = None

            if timeout is not None:
                remaining = (
                    timeout
                    - (
                        time.perf_counter()
                        - started
                    )
                )

                if remaining <= 0:
                    raise TimeoutError(
                        "Host health check timed out."
                    )

            results.append(
                self.check_host(
                    hostname,
                    timeout=remaining,
                )
            )

        return results


    def check_all_hosts(
        self,
        timeout=None,
    ):
        hosts = self.inventory.all_hosts()

        hostnames = [
            host["hostname"]
            for host in hosts
        ]

        return self.check_hosts(
            hostnames,
            timeout=timeout,
        )


    def latest(
        self,
        hostname,
        check=None,
    ):

        return self.repository.latest(
            hostname=hostname,
            check=check or self.CHECK_NAME,
        )

    def host(
        self,
        hostname,
        limit=50,
    ):

        return self.repository.host(
            hostname=hostname,
            limit=limit,
        )

    def history(
        self,
        hostname=None,
        limit=50,
    ):

        if hostname is None:

            return self.repository.history(
                limit=limit,
            )

        return self.repository.host(
            hostname=hostname,
            limit=limit,
        )
