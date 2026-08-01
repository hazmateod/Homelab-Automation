"""
Git helper functions.
"""

import subprocess


def current_branch():
    result = subprocess.run(
        [
            "git",
            "branch",
            "--show-current",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    return result.stdout.strip()

def is_clean():
    result = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    return result.stdout.strip() == ""
