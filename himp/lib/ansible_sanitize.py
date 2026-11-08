"""Fail-closed sanitization for Ansible execution events."""

import re


MAX_STRING_LENGTH = 2000
MAX_COLLECTION_ITEMS = 100
MAX_DEPTH = 12

SENSITIVE_KEY = re.compile(
    r"password|passwd|passphrase|token|secret|"
    r"api[_-]?key|access[_-]?key|private[_-]?key|"
    r"authorization|proxy[_-]?authorization|"
    r"cookie|credential|client[_-]?secret",
    re.IGNORECASE,
)

REDACTION_PATTERNS = [
    (
        re.compile(
            r'(?i)(\b[a-z][a-z0-9+.-]*://)[^/@\s]+@'
        ),
        r'\1[REDACTED]@',
    ),

    (
        re.compile(
            r'(?i)(\buser(?:name)?\s*[:=]\s*)'
            r'("[^"]*"|\'[^\']*\'|[^\s,;&]+)'
        ),
        r'\1[REDACTED]',
    ),

    (
        re.compile(
            r'(?i)(["\']?(?:password|passwd|passphrase|'
            r'token|secret|api[_-]?key|access[_-]?key|'
            r'client[_-]?secret|authorization)'
            r'["\']?\s*[:=]\s*)'
            r'("[^"]*"|\'[^\']*\'|[^\s,;&]+)'
        ),
        r'\1[REDACTED]',
    ),
    (
        re.compile(
            r'(?i)(https?://)[^/\s:@]+:[^@\s/]+@'
        ),
        r'\1[REDACTED]@',
    ),
    (
        re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+'),
        'Bearer [REDACTED]',
    ),
    (
        re.compile(r'(?i)\bBasic\s+[A-Za-z0-9+/=]+'),
        'Basic [REDACTED]',
    ),
    (
        re.compile(
            r'(?im)^(\s*(?:authorization|proxy-authorization|'
            r'cookie|set-cookie)\s*:\s*).+$'
        ),
        r'\1[REDACTED]',
    ),
    (
        re.compile(
            r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'
            r'.*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
            re.DOTALL,
        ),
        '[REDACTED PRIVATE KEY]',
    ),
]


def sanitize_string(value):
    """Redact embedded credentials and bound diagnostic output."""
    if not isinstance(value, str):
        raise TypeError("Expected string")

    result = value

    for pattern, replacement in REDACTION_PATTERNS:
        result = pattern.sub(replacement, result)

    if len(result) > MAX_STRING_LENGTH:
        result = result[:MAX_STRING_LENGTH] + "...[TRUNCATED]"

    return result


def sanitize_value(value, depth=0):
    """Recursively sanitize supported JSON-compatible values."""
    if depth > MAX_DEPTH:
        return "[MAXIMUM DEPTH EXCEEDED]"

    if isinstance(value, dict):
        result = {}

        for index, (key, item) in enumerate(value.items()):
            if index >= MAX_COLLECTION_ITEMS:
                result["_truncated"] = True
                break

            safe_key = sanitize_string(str(key))[:128]

            if SENSITIVE_KEY.search(safe_key):
                result[safe_key] = "[REDACTED]"
            else:
                result[safe_key] = sanitize_value(
                    item,
                    depth + 1,
                )

        return result

    if isinstance(value, (list, tuple)):
        result = [
            sanitize_value(item, depth + 1)
            for item in value[:MAX_COLLECTION_ITEMS]
        ]

        if len(value) > MAX_COLLECTION_ITEMS:
            result.append("[TRUNCATED]")

        return result

    if isinstance(value, str):
        return sanitize_string(value)

    if value is None or isinstance(value, (bool, int, float)):
        return value

    # Never serialize unknown objects or their potentially sensitive repr.
    return "[UNSUPPORTED VALUE]"


def sanitize_event(payload):
    """Sanitize an entire event before serialization."""
    result = sanitize_value(payload)

    if not isinstance(result, dict):
        raise ValueError("Invalid event payload")

    return result
