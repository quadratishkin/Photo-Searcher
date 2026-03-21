from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import Lock
from typing import BinaryIO


MODEL_NAME = "ViT-B-32"
PRETRAINED_TAG = "laion2b_s34b_b79k"


@dataclass(frozen=True)
class EngineMetadata:
    model_name: str
    pretrained_tag: str
    device: str
    embedding_dimension: int


@dataclass
class RuntimeStatus:
    state: str
    summary: str
    details: str
    reason: str


@dataclass(frozen=True)
class ModelBundle:
    model: object
    preprocess: object
    device: str
    embedding_dimension: int


_model_bundle: ModelBundle | None = None
_model_lock = Lock()
_runtime_status = RuntimeStatus(
    state="idle",
    summary="OpenCLIP не загружен",
    details="Модель будет поднята при первой загрузке фото",
    reason="Ленивая инициализация для server-side embedding pipeline.",
)


def _detect_device() -> str:
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def _load_model_bundle() -> ModelBundle:
    global _model_bundle, _runtime_status

    with _model_lock:
        if _model_bundle is not None:
            return _model_bundle

        try:
            import open_clip
            import torch
        except ImportError as exc:
            _runtime_status = RuntimeStatus(
                state="missing_dependency",
                summary="Нет AI-зависимостей",
                details="open_clip_torch и torch не установлены",
                reason=str(exc),
            )
            raise RuntimeError("OpenCLIP зависимости не установлены.") from exc

        device = _detect_device()
        model, _, preprocess = open_clip.create_model_and_transforms(
            MODEL_NAME,
            pretrained=PRETRAINED_TAG,
            device=device,
        )
        model.eval()

        with torch.no_grad():
            probe = torch.zeros((1, 3, 224, 224), device=device)
            probe_features = model.encode_image(probe)
        embedding_dimension = int(probe_features.shape[-1])

        _model_bundle = ModelBundle(
            model=model,
            preprocess=preprocess,
            device=device,
            embedding_dimension=embedding_dimension,
        )
        _runtime_status = RuntimeStatus(
            state="ready",
            summary="OpenCLIP активен",
            details=f"{MODEL_NAME} / {PRETRAINED_TAG} / {device}",
            reason="Image embedding pipeline готов к обработке новых фото.",
        )
        return _model_bundle


def get_engine_metadata() -> dict[str, str | int]:
    bundle = _load_model_bundle()
    metadata = EngineMetadata(
        model_name=MODEL_NAME,
        pretrained_tag=PRETRAINED_TAG,
        device=bundle.device,
        embedding_dimension=bundle.embedding_dimension,
    )
    return asdict(metadata)


def get_runtime_status() -> dict[str, str]:
    return asdict(_runtime_status)


def create_image_embedding(file_obj: BinaryIO) -> dict[str, object]:
    from PIL import Image
    import torch

    bundle = _load_model_bundle()

    image = Image.open(file_obj)
    image = image.convert("RGB")
    image_tensor = bundle.preprocess(image).unsqueeze(0).to(bundle.device)

    with torch.no_grad():
        image_features = bundle.model.encode_image(image_tensor)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)

    vector = image_features.squeeze(0).detach().cpu().tolist()
    return {
        "model_name": MODEL_NAME,
        "pretrained_tag": PRETRAINED_TAG,
        "device": bundle.device,
        "dimension": bundle.embedding_dimension,
        "vector": vector,
    }


def create_text_embedding(query: str) -> dict[str, object]:
    import open_clip
    import torch

    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("Текстовый запрос не должен быть пустым.")

    bundle = _load_model_bundle()
    tokenizer = open_clip.get_tokenizer(MODEL_NAME)
    tokens = tokenizer([normalized_query]).to(bundle.device)

    with torch.no_grad():
        text_features = bundle.model.encode_text(tokens)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)

    vector = text_features.squeeze(0).detach().cpu().tolist()
    return {
        "model_name": MODEL_NAME,
        "pretrained_tag": PRETRAINED_TAG,
        "device": bundle.device,
        "dimension": bundle.embedding_dimension,
        "vector": vector,
    }
