from __future__ import annotations

import hashlib


def generateHash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
