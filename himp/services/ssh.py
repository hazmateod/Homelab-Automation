"""
SSH connectivity service.
"""

import subprocess
import time

from himp.models.ssh import SSHResult


class SSHService:
    """
    Provides non-interactive SSH connectivity tests.
    """

    CONNECT_TIMEOUT = 5

    def test(
        self,
        hostname,
        ip,
        user,
        timeout=None,
    ):
        result = SSHResult(
            hostname=hostname,
            ip=ip,
            user=user,
        )

        connect_timeout = (
            self.CONNECT_TIMEOUT
            if timeout is None
            else min(
                self.CONNECT_TIMEOUT,
                max(float(timeout), 0.1),
            )
        )

        command = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            f"ConnectTimeout={connect_timeout}",
            f"{user}@{ip}",
            "true",
        ]

        start = time.perf_counter()

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=(
                    connect_timeout + 2
                ),
            )

        except subprocess.TimeoutExpired:
            result.status = "TIMEOUT"
            result.message = (
                "SSH connection timed out."
            )
            result.elapsed = round(
                time.perf_counter() - start,
                3,
            )

            return result

        except OSError as exc:
            result.status = "ERROR"
            result.message = str(exc)
            result.elapsed = round(
                time.perf_counter() - start,
                3,
            )

            return result

        result.elapsed = round(
            time.perf_counter() - start,
            3,
        )

        result.return_code = process.returncode
        result.stdout = process.stdout.strip()
        result.stderr = process.stderr.strip()

        if process.returncode == 0:
            result.status = "READY"
            result.success = True
            result.message = (
                "SSH authentication successful."
            )

            return result

        stderr = result.stderr.lower()

        if (
            "permission denied" in stderr
            or "authentication" in stderr
        ):
            result.status = "AUTHENTICATION_FAILED"
            result.message = (
                "SSH authentication failed."
            )

        elif (
            "connection timed out" in stderr
            or "operation timed out" in stderr
        ):
            result.status = "TIMEOUT"
            result.message = (
                "SSH connection timed out."
            )

        elif (
            "connection refused" in stderr
            or "could not resolve hostname" in stderr
            or "no route to host" in stderr
            or "network is unreachable" in stderr
        ):
            result.status = "UNREACHABLE"
            result.message = (
                "SSH host is unreachable."
            )

        else:
            result.status = "ERROR"
            result.message = (
                "SSH connection failed."
            )

        return result
