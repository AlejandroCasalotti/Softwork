import json


SENSITIVE_KEYS = {
    "authorization",
    "api_key",
    "apikey",
    "password",
    "access_token",
    "refresh_token",
    "client_secret",
    "secret",
    "cookie",
    "set-cookie",
    "bearer",
}


def _is_sensitive_key(key):
    normalized = str(key).strip().lower().replace("-", "_")
    return normalized in SENSITIVE_KEYS or any(
        marker in normalized
        for marker in ("token", "password", "secret", "api_key", "authorization", "cookie")
    )


def redact(value):
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _is_sensitive_key(key) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        result = value
        for marker in ("Bearer ", "Basic "):
            if marker in result:
                prefix, _, _ = result.partition(marker)
                result = f"{prefix}{marker}[REDACTED]"
        return result
    return value


def redact_json(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return redact(value)
    return redact(value)
