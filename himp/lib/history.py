"""
History helper functions.
"""

from datetime import datetime
from pathlib import Path


HISTORY_FILE = Path("logs/history.log")


def log(command, success, elapsed):

    HISTORY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    status = "SUCCESS" if success else "FAILED"

    with HISTORY_FILE.open(
        "a",
        encoding="utf-8",
    ) as f:

        f.write(
            f"{timestamp}|{command}|{status}|{elapsed:.2f}\n"
        )
