"""Stable fingerprints for authenticated mutation requests."""

import hashlib
import json


def operation_fingerprint(action: str, payload: dict[str, object]) -> str:
    serialized = json.dumps(
        {"action": action, "payload": payload},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class IdempotencyConflictError(Exception):
    """An actor reused an operation key with a different resource or payload."""
