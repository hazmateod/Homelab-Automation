import pytest

from himp.services.automation import AutomationService


@pytest.mark.parametrize(
    "error,category,retryable",
    [
        (
            TimeoutError("timed out"),
            "timeout",
            True,
        ),
        (
            OSError("connection refused"),
            "unreachable",
            True,
        ),
        (
            RuntimeError("execution failed"),
            "execution",
            True,
        ),
        (
            ValueError("unexpected value"),
            "internal",
            False,
        ),
        (
            Exception("unexpected failure"),
            "internal",
            False,
        ),
    ],
)
def test_classify_error_returns_expected_category(
    error,
    category,
    retryable,
):
    result = AutomationService._classify_error(
        error
    )

    assert result == {
        "category": category,
        "retryable": retryable,
    }
