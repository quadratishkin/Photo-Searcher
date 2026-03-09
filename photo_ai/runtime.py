from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock


CONFIG_FILE_NAME = "CoreAI.config"


@dataclass
class AiModuleStatus:
    enabled: bool
    state: str
    summary: str
    details: str
    reason: str


_status_lock = Lock()
_has_attempted_load = False
_status = AiModuleStatus(
    enabled=False,
    state="idle",
    summary="Модуль не запускался",
    details="Ожидает инициализации",
    reason="Функция инициализации ещё не вызывалась.",
)


def _get_config_path() -> Path:
    return Path(__file__).resolve().parent.parent / CONFIG_FILE_NAME


def _parse_config_file() -> dict[str, str]:
    config: dict[str, str] = {}
    config_path = _get_config_path()
    if not config_path.exists():
        return config

    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        config[key.strip()] = value.strip()
    return config


def _is_enabled(raw_value: str | None) -> bool:
    return (raw_value or "").strip().lower() in {"1", "true", "yes", "on"}


def load_ai_module() -> dict[str, str | bool]:
    global _has_attempted_load, _status

    with _status_lock:
        if _has_attempted_load:
            return asdict(_status)

        _has_attempted_load = True
        config = _parse_config_file()
        enabled = _is_enabled(config.get("bEnableAiModule"))

        if not enabled:
            _status = AiModuleStatus(
                enabled=False,
                state="disabled",
                summary="Модуль отключен",
                details="CoreAI.config: bEnableAiModule=false",
                reason="AI-модуль отключён в корневом конфиге.",
            )
            return asdict(_status)

        # Placeholder startup path for future model and pipeline loading.
        _status = AiModuleStatus(
            enabled=True,
            state="placeholder",
            summary="Placeholder активен",
            details="Реальная AI-логика пока не подключена",
            reason="Запущен базовый placeholder AI-модуля.",
        )
        return asdict(_status)


def get_ai_module_status() -> dict[str, str | bool]:
    with _status_lock:
        return asdict(_status)
