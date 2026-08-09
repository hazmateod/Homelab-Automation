"""
SSH connectivity models.
"""

from dataclasses import dataclass


@dataclass
class SSHResult:
    hostname: str
    ip: str
    user: str
    status: str = "UNKNOWN"
    success: bool = False
    return_code: int = 0
    elapsed: float = 0.0
    stdout: str = ""
    stderr: str = ""
    message: str = ""
