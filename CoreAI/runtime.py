from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from threading import RLock

from . import embeddings


CONFIG_FILE_NAME = "CoreAI.config"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


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


def _parse_config_file() -> dict[str, str]:
    config: dict[str, str] = {}
    config_path = PROJECT_ROOT / CONFIG_FILE_NAME
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


def _get_configured_embeddings(config: dict[str, str] | None = None):
    embeddings.configure_runtime(config or _parse_config_file())
    return embeddings


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

        shipping = _get_configured_embeddings(config)
        shipping_status = shipping.warm_runtime()

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
    global _has_attempted_load, _status

    with _status_lock:
        if not _has_attempted_load:
            return load_ai_module()

        config = _parse_config_file()
        if not _is_enabled(config.get("bEnableAiModule")):
            return load_ai_module()

        shipping = _get_configured_embeddings(config)
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


def get_embedding_engine_metadata() -> dict[str, str | int]:
    shipping = _get_configured_embeddings()
    return shipping.get_engine_metadata()


def create_image_embedding(file_obj) -> dict[str, object]:
    config = _parse_config_file()
    enabled = _is_enabled(config.get("bEnableAiModule"))
    if not enabled:
        raise RuntimeError("AI-модуль отключён в CoreAI.config.")

    shipping = _get_configured_embeddings(config)
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

    shipping = _get_configured_embeddings(config)
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


def rewrite_search_query(query: str) -> dict[str, str | bool]:
    config = _parse_config_file()
    enabled = _is_enabled(config.get("bEnableAiModule"))
    if not enabled:
        raise RuntimeError("AI-модуль отключён в CoreAI.config.")

    shipping = _get_configured_embeddings(config)
    result = shipping.rewrite_search_query(query)

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


def create_photo_index(file_obj) -> dict[str, object]:
    config = _parse_config_file()
    enabled = _is_enabled(config.get("bEnableAiModule"))
    if not enabled:
        raise RuntimeError("AI-модуль отключён в CoreAI.config.")

    shipping = _get_configured_embeddings(config)
    result = shipping.create_photo_index(file_obj)

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


def translate_text_to_english(text: str) -> str:
    config = _parse_config_file()
    enabled = _is_enabled(config.get("bEnableAiModule"))
    if not enabled:
        raise RuntimeError("AI-модуль отключён в CoreAI.config.")

    shipping = _get_configured_embeddings(config)
    result = shipping.translate_text_to_english(text)

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


def warm_ai_runtime() -> dict[str, str | bool]:
    config = _parse_config_file()
    enabled = _is_enabled(config.get("bEnableAiModule"))
    if not enabled:
        return load_ai_module()

    shipping = _get_configured_embeddings(config)
    shipping_status = shipping.warm_runtime()

    with _status_lock:
        global _has_attempted_load, _status
        _has_attempted_load = True
        _status = AiModuleStatus(
            enabled=True,
            state=str(shipping_status["state"]),
            summary=str(shipping_status["summary"]),
            details=str(shipping_status["details"]),
            reason=str(shipping_status["reason"]),
        )
        return asdict(_status)
