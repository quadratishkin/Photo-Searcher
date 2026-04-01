from __future__ import annotations

import os
from pathlib import Path


def _iter_env_lines(raw_text: str):
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        yield key, value


def load_project_env() -> None:
    project_root = Path(__file__).resolve().parents[2]
    for filename in (".env.local", ".env"):
        env_path = project_root / filename
        if not env_path.exists():
            continue
        for key, value in _iter_env_lines(env_path.read_text(encoding="utf-8")):
            os.environ.setdefault(key, value)
