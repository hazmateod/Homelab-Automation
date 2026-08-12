import logging

from himp.lib.logging_config import configure_logging


def test_configure_logging_sets_himp_logger_level():
    configure_logging()

    logger = logging.getLogger("himp")

    assert logger.level == logging.INFO


def test_configure_logging_is_idempotent():
    configure_logging()

    logger = logging.getLogger("himp")
    handler_count = len(logger.handlers)

    configure_logging()

    assert len(logger.handlers) == handler_count


def test_himp_initialization_emits_startup_log():
    from himp.app import HIMP

    records = []

    class CaptureHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    logger = logging.getLogger("himp")
    handler = CaptureHandler()
    logger.addHandler(handler)

    try:
        HIMP()
    finally:
        logger.removeHandler(handler)

    assert any(
        record.name == "himp"
        and record.message == "HIMP application initialized"
        for record in records
    )
