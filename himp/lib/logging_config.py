"""
HIMP logging configuration.
"""

import logging
import sys


def configure_logging():
    logger = logging.getLogger("himp")

    if logger.handlers:
        logger.setLevel(logging.INFO)
        return

    handler = logging.StreamHandler(sys.stderr)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
