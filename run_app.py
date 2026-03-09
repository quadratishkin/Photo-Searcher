from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_BIND = "127.0.0.1:8000"


def run_command(command: list[str]) -> None:
    subprocess.run(["cmd", "/c", *command], cwd=BASE_DIR, check=True)


def ensure_frontend_dependencies() -> None:
    if not (BASE_DIR / "node_modules").exists():
        run_command(["pnpm", "install"])


def build_frontend() -> None:
    run_command(["pnpm", "build"])


def apply_migrations() -> None:
    subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], cwd=BASE_DIR, check=True)


def start_server(bind: str) -> None:
    os.execv(
        sys.executable,
        [sys.executable, "manage.py", "runserver", bind],
    )


def main() -> None:
    bind = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BIND
    ensure_frontend_dependencies()
    build_frontend()
    apply_migrations()
    start_server(bind)


if __name__ == "__main__":
    main()
