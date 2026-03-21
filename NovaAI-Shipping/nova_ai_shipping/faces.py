from __future__ import annotations

from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
from threading import RLock

import numpy as np
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE_NAME = "CoreAI.config"
DEFAULT_FACE_MODEL_PACK = "buffalo_l"
DEFAULT_FACE_PROVIDER = "auto"
DEFAULT_FACE_MODEL_ROOT = "NovaAI-Shipping/models/insightface"
DEFAULT_FACE_DET_SIZE = 640
DEFAULT_FACE_MIN_SCORE = 0.55
DEFAULT_FACE_MIN_SIZE = 56
DEFAULT_CLUSTER_EPS = 0.62


@dataclass(frozen=True)
class FaceRuntimeConfig:
    enabled: bool
    model_pack: str
    provider: str
    model_root: str
    detection_size: int
    min_confidence: float
    min_face_size: int
    cluster_eps: float


@dataclass
class FaceRuntimeStatus:
    enabled: bool
    state: str
    summary: str
    details: str
    reason: str


_runtime_lock = RLock()
_runtime_app = None
_runtime_config = FaceRuntimeConfig(
    enabled=True,
    model_pack=DEFAULT_FACE_MODEL_PACK,
    provider=DEFAULT_FACE_PROVIDER,
    model_root=str((PROJECT_ROOT / DEFAULT_FACE_MODEL_ROOT).resolve()),
    detection_size=DEFAULT_FACE_DET_SIZE,
    min_confidence=DEFAULT_FACE_MIN_SCORE,
    min_face_size=DEFAULT_FACE_MIN_SIZE,
    cluster_eps=DEFAULT_CLUSTER_EPS,
)
_runtime_status = FaceRuntimeStatus(
    enabled=True,
    state="idle",
    summary="Модуль лиц не запускался",
    details="Ожидает первой обработки фотографии",
    reason="Face pipeline ещё не инициализирован.",
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


def _is_enabled(raw_value: str | None, *, default: bool = False) -> bool:
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_project_path(value: str) -> str:
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return str(candidate)
    return str((PROJECT_ROOT / candidate).resolve())


def _read_int(raw_value: str | None, default: int) -> int:
    try:
        return max(1, int(str(raw_value).strip()))
    except (TypeError, ValueError):
        return default


def _read_float(raw_value: str | None, default: float) -> float:
    try:
        return float(str(raw_value).strip())
    except (TypeError, ValueError):
        return default


def _normalize_config(config: dict[str, str] | None = None) -> FaceRuntimeConfig:
    source = config or _parse_config_file()
    provider = str(source.get("sFaceExecutionProvider", DEFAULT_FACE_PROVIDER)).strip() or DEFAULT_FACE_PROVIDER
    if provider not in {"auto", "cpu", "cuda", "coreml"}:
        provider = DEFAULT_FACE_PROVIDER

    model_root = str(source.get("sFaceModelRoot", DEFAULT_FACE_MODEL_ROOT)).strip() or DEFAULT_FACE_MODEL_ROOT
    cluster_eps = _read_float(source.get("fFaceClusterEps"), DEFAULT_CLUSTER_EPS)
    cluster_eps = min(0.95, max(0.05, cluster_eps))

    return FaceRuntimeConfig(
        enabled=_is_enabled(source.get("bEnableAiModule"), default=False)
        and _is_enabled(source.get("bEnableFaceModule"), default=True),
        model_pack=str(source.get("sFaceModelPack", DEFAULT_FACE_MODEL_PACK)).strip() or DEFAULT_FACE_MODEL_PACK,
        provider=provider,
        model_root=_resolve_project_path(model_root),
        detection_size=_read_int(source.get("nFaceDetectionSize"), DEFAULT_FACE_DET_SIZE),
        min_confidence=min(0.99, max(0.0, _read_float(source.get("fFaceMinConfidence"), DEFAULT_FACE_MIN_SCORE))),
        min_face_size=_read_int(source.get("nFaceMinSize"), DEFAULT_FACE_MIN_SIZE),
        cluster_eps=cluster_eps,
    )


def _provider_candidates(preferred_provider: str) -> list[str]:
    import onnxruntime

    available = set(onnxruntime.get_available_providers())
    order: list[str]
    if preferred_provider == "cuda":
        order = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    elif preferred_provider == "coreml":
        order = ["CoreMLExecutionProvider", "CPUExecutionProvider"]
    elif preferred_provider == "cpu":
        order = ["CPUExecutionProvider"]
    else:
        order = ["CUDAExecutionProvider", "CoreMLExecutionProvider", "CPUExecutionProvider"]

    return [provider for provider in order if provider in available]


def _get_runtime_app():
    global _runtime_app, _runtime_status, _runtime_config

    with _runtime_lock:
        config = _normalize_config()
        if config != _runtime_config:
            _runtime_config = config
            _runtime_app = None
            _runtime_status = FaceRuntimeStatus(
                enabled=config.enabled,
                state="idle",
                summary="Параметры face pipeline обновлены",
                details="Модель лиц будет загружена при следующем запросе",
                reason="Конфигурация изменилась.",
            )

        if not config.enabled:
            _runtime_status = FaceRuntimeStatus(
                enabled=False,
                state="disabled",
                summary="Группировка людей отключена",
                details="CoreAI.config: bEnableFaceModule=false или отключён AI-модуль",
                reason="Face pipeline выключен в конфиге.",
            )
            raise RuntimeError("Face pipeline отключён в CoreAI.config.")

        if _runtime_app is not None:
            return _runtime_app

        try:
            from insightface.app import FaceAnalysis
        except ImportError as exc:
            _runtime_status = FaceRuntimeStatus(
                enabled=True,
                state="missing_dependency",
                summary="Нет зависимостей для работы с лицами",
                details="insightface или onnxruntime не установлены",
                reason=str(exc),
            )
            raise RuntimeError("InsightFace зависимости не установлены.") from exc

        providers = _provider_candidates(config.provider)
        if not providers:
            _runtime_status = FaceRuntimeStatus(
                enabled=True,
                state="missing_dependency",
                summary="Нет ONNX Runtime provider",
                details="onnxruntime не сообщил доступных execution providers",
                reason="InsightFace не может выбрать backend для face analysis.",
            )
            raise RuntimeError("Не найден ONNX Runtime provider для face pipeline.")

        model_root = Path(config.model_root)
        model_root.mkdir(parents=True, exist_ok=True)

        app = FaceAnalysis(name=config.model_pack, root=str(model_root), providers=providers)
        primary_provider = providers[0]
        ctx_id = -1 if primary_provider == "CPUExecutionProvider" else 0
        app.prepare(ctx_id=ctx_id, det_size=(config.detection_size, config.detection_size))
        _runtime_app = app
        _runtime_status = FaceRuntimeStatus(
            enabled=True,
            state="ready",
            summary="Группировка людей активна",
            details=f"{config.model_pack} / {primary_provider}",
            reason="Face detection и face embedding pipeline готовы.",
        )
        return _runtime_app


def get_face_runtime_status() -> dict[str, str | bool]:
    try:
        _get_runtime_app()
    except Exception:
        pass
    return asdict(_runtime_status)


def get_face_runtime_config() -> dict[str, object]:
    return asdict(_normalize_config())


def _normalized_embedding(vector: np.ndarray) -> list[float]:
    norm = float(np.linalg.norm(vector))
    if norm <= 0:
        raise RuntimeError("Face embedding имеет нулевую длину.")
    normalized = vector / norm
    return normalized.astype(np.float32).tolist()


def _clamp_bbox(bbox: list[float], width: int, height: int) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = bbox
    return (
        max(0, min(width, int(round(x1)))),
        max(0, min(height, int(round(y1)))),
        max(0, min(width, int(round(x2)))),
        max(0, min(height, int(round(y2)))),
    )


def _build_face_preview(image: Image.Image, bbox: list[float]) -> bytes:
    width, height = image.size
    x1, y1, x2, y2 = _clamp_bbox(bbox, width, height)
    face_width = max(1, x2 - x1)
    face_height = max(1, y2 - y1)
    padding = int(round(max(face_width, face_height) * 0.28))

    crop_box = (
        max(0, x1 - padding),
        max(0, y1 - padding),
        min(width, x2 + padding),
        min(height, y2 + padding),
    )
    crop = image.crop(crop_box).resize((320, 320), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    crop.save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()


def extract_faces(file_obj) -> list[dict[str, object]]:
    config = _normalize_config()
    if not config.enabled:
        raise RuntimeError("Face pipeline отключён в CoreAI.config.")

    payload = file_obj.read()
    if not payload:
        return []

    image = Image.open(BytesIO(payload)).convert("RGB")
    image_np = np.array(image)
    bgr_image = image_np[:, :, ::-1]

    app = _get_runtime_app()
    faces = app.get(bgr_image)
    detected_faces: list[dict[str, object]] = []
    max_dimension = max(image.width, image.height, 1)

    for face in faces:
        bbox = [float(value) for value in np.asarray(face.bbox).tolist()]
        x1, y1, x2, y2 = bbox
        face_width = max(0.0, x2 - x1)
        face_height = max(0.0, y2 - y1)
        face_size = min(face_width, face_height)
        det_score = float(getattr(face, "det_score", 0.0) or 0.0)
        if det_score < config.min_confidence or face_size < config.min_face_size:
            continue

        embedding = getattr(face, "embedding", None)
        if embedding is None:
            continue

        preview_bytes = _build_face_preview(image, bbox)
        quality_score = float((det_score * face_size) / max_dimension)
        detected_faces.append(
            {
                "bbox": bbox,
                "landmarks": [
                    [float(point[0]), float(point[1])]
                    for point in np.asarray(getattr(face, "kps", np.empty((0, 2)))).tolist()
                ],
                "detection_score": det_score,
                "quality_score": quality_score,
                "embedding_model": config.model_pack,
                "embedding_dimension": len(embedding),
                "embedding_vector": _normalized_embedding(np.asarray(embedding, dtype=np.float32)),
                "preview_bytes": preview_bytes,
            }
        )

    return detected_faces
