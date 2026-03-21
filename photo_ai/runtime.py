from __future__ import annotations

import importlib
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import RLock


CONFIG_FILE_NAME = "CoreAI.config"
SHIPPING_DIR_NAME = "NovaAI-Shipping"


@dataclass
class AiModuleStatus:
    enabled: bool
    state: str
    summary: str
    details: str
    reason: str


_status_lock = RLock()
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


def _get_shipping_dir() -> Path:
    return Path(__file__).resolve().parent.parent / SHIPPING_DIR_NAME


def _ensure_shipping_module_path() -> None:
    shipping_dir = _get_shipping_dir()
    shipping_dir_str = str(shipping_dir)
    if shipping_dir_str not in sys.path:
        sys.path.insert(0, shipping_dir_str)


def _get_shipping_module():
    _ensure_shipping_module_path()
    return importlib.import_module("nova_ai_shipping")


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
        config = _parse_config_file()
        enabled = _is_enabled(config.get("bEnableAiModule"))

        if not enabled:
            _has_attempted_load = True
            _status = AiModuleStatus(
                enabled=False,
                state="disabled",
                summary="Модуль отключен",
                details="CoreAI.config: bEnableAiModule=false",
                reason="AI-модуль отключён в корневом конфиге.",
            )
            return asdict(_status)

        shipping = _get_shipping_module()
        shipping_status = shipping.get_runtime_status()

        _has_attempted_load = True
        _status = AiModuleStatus(
            enabled=True,
            state=str(shipping_status["state"]),
            summary=str(shipping_status["summary"]),
            details=str(shipping_status["details"]),
            reason=str(shipping_status["reason"]),
        )
        return asdict(_status)


def get_ai_module_status() -> dict[str, str | bool]:
    with _status_lock:
        if not _has_attempted_load:
            return load_ai_module()
        return asdict(_status)


def get_embedding_engine_metadata() -> dict[str, str | int]:
    shipping = _get_shipping_module()
    return shipping.get_engine_metadata()


def create_image_embedding(file_obj) -> dict[str, object]:
    config = _parse_config_file()
    enabled = _is_enabled(config.get("bEnableAiModule"))
    if not enabled:
        raise RuntimeError("AI-модуль отключён в CoreAI.config.")

    shipping = _get_shipping_module()
    result = shipping.create_image_embedding(file_obj)

    with _status_lock:
        global _has_attempted_load, _status
        _has_attempted_load = True
        shipping_status = shipping.get_runtime_status()
        _status = AiModuleStatus(
            enabled=True,
            state=str(shipping_status["state"]),
            summary=str(shipping_status["summary"]),
            details=str(shipping_status["details"]),
            reason=str(shipping_status["reason"]),
        )

    return result


def create_text_embedding(query: str) -> dict[str, object]:
    config = _parse_config_file()
    enabled = _is_enabled(config.get("bEnableAiModule"))
    if not enabled:
        raise RuntimeError("AI-модуль отключён в CoreAI.config.")

    shipping = _get_shipping_module()
    result = shipping.create_text_embedding(query)

    with _status_lock:
        global _has_attempted_load, _status
        _has_attempted_load = True
        shipping_status = shipping.get_runtime_status()
        _status = AiModuleStatus(
            enabled=True,
            state=str(shipping_status["state"]),
            summary=str(shipping_status["summary"]),
            details=str(shipping_status["details"]),
            reason=str(shipping_status["reason"]),
        )

    return result
