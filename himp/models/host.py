"""
Host model.
"""

from dataclasses import dataclass


@dataclass
class Host:
    hostname: str
    ip: str
    os: str
    kernel: str
    score: int
    status: str

    def is_healthy(self):
        return self.status == "HEALTHY"

    def is_warning(self):
        return self.status == "WARNING"

    def is_critical(self):
        return self.status == "CRITICAL"

    def is_unknown(self):
        return not (
            self.is_healthy()
            or self.is_warning()
            or self.is_critical()
        )
