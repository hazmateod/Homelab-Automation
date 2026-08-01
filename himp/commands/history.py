"""
History Commands
"""

from pathlib import Path

from himp.lib.output import error


HISTORY_FILE = Path("logs/history.log")


def run(args):

    if not HISTORY_FILE.exists():
        error("No command history found.")
        return

    print("HIMP Command History")
    print("====================")
    print()

    print(
        f"{'Timestamp':<20} "
        f"{'Command':<20} "
        f"{'Status':<10} "
        f"{'Time':>8}"
    )

    print("-" * 62)

    with HISTORY_FILE.open(
        encoding="utf-8",
    ) as f:

        for line in f:

            timestamp, command, status, elapsed = (
                line.rstrip().split("|")
            )

            print(
                f"{timestamp:<20} "
                f"{command:<20} "
                f"{status:<10} "
                f"{elapsed:>8}s"
            )
