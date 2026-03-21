from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from threading import Lock
from typing import BinaryIO


MODEL_NAME = "ViT-B-32"
PRETRAINED_TAG = "laion2b_s34b_b79k"
CAPTION_MODEL_NAME = "Salesforce/blip-image-captioning-base"
TRANSLATION_MODEL_NAME = "Helsinki-NLP/opus-mt-ru-en"
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


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


@dataclass(frozen=True)
class CaptionBundle:
    processor: object
    model: object
    device: str


@dataclass(frozen=True)
class TranslationBundle:
    tokenizer: object
    model: object


_model_bundle: ModelBundle | None = None
_model_lock = Lock()
_caption_bundle: CaptionBundle | None = None
_caption_lock = Lock()
_translation_bundle: TranslationBundle | None = None
_translation_lock = Lock()
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


def _load_caption_bundle() -> CaptionBundle:
    global _caption_bundle

    with _caption_lock:
        if _caption_bundle is not None:
            return _caption_bundle

        try:
            from transformers import BlipForConditionalGeneration, BlipProcessor
        except ImportError as exc:
            raise RuntimeError("BLIP зависимости не установлены.") from exc

        device = _detect_device()
        processor = BlipProcessor.from_pretrained(CAPTION_MODEL_NAME)
        model = BlipForConditionalGeneration.from_pretrained(CAPTION_MODEL_NAME).to(device)
        model.eval()

        _caption_bundle = CaptionBundle(
            processor=processor,
            model=model,
            device=device,
        )
        return _caption_bundle


def _load_translation_bundle() -> TranslationBundle:
    global _translation_bundle

    with _translation_lock:
        if _translation_bundle is not None:
            return _translation_bundle

        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError("Translation зависимости не установлены.") from exc

        tokenizer = AutoTokenizer.from_pretrained(TRANSLATION_MODEL_NAME)
        model = AutoModelForSeq2SeqLM.from_pretrained(TRANSLATION_MODEL_NAME)
        model.eval()

        _translation_bundle = TranslationBundle(tokenizer=tokenizer, model=model)
        return _translation_bundle


def normalize_english_text(text: str) -> str:
    normalized = text.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def extract_search_tokens(text: str) -> list[str]:
    normalized = normalize_english_text(text)
    tokens = TOKEN_PATTERN.findall(normalized)
    unique_tokens: list[str] = []
    seen_tokens: set[str] = set()
    for token in tokens:
        if len(token) <= 1 or token in seen_tokens:
            continue
        seen_tokens.add(token)
        unique_tokens.append(token)
    return unique_tokens


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


def generate_caption(file_obj: BinaryIO) -> str:
    from PIL import Image
    import torch

    bundle = _load_caption_bundle()

    image = Image.open(file_obj)
    image = image.convert("RGB")
    inputs = bundle.processor(images=image, return_tensors="pt")
    prepared_inputs = {name: value.to(bundle.device) for name, value in inputs.items()}

    with torch.no_grad():
        output_tokens = bundle.model.generate(
            **prepared_inputs,
            max_new_tokens=32,
            num_beams=4,
        )

    caption = bundle.processor.decode(output_tokens[0], skip_special_tokens=True).strip()
    if not caption:
        raise RuntimeError("BLIP не смог сгенерировать описание изображения.")
    return normalize_english_text(caption)


def translate_text_to_english(text: str) -> str:
    import torch

    normalized_text = text.strip()
    if not normalized_text:
        raise ValueError("Текст для перевода не должен быть пустым.")

    if not any("а" <= char.lower() <= "я" or char.lower() == "ё" for char in normalized_text):
        return normalize_english_text(normalized_text)

    bundle = _load_translation_bundle()
    inputs = bundle.tokenizer(normalized_text, return_tensors="pt", truncation=True)

    with torch.no_grad():
        output_tokens = bundle.model.generate(**inputs, max_new_tokens=64)

    translated = bundle.tokenizer.decode(output_tokens[0], skip_special_tokens=True).strip()
    if not translated:
        raise RuntimeError("Не удалось перевести запрос на английский.")
    return normalize_english_text(translated)


def create_photo_index(file_obj: BinaryIO) -> dict[str, object]:
    image_embedding = create_image_embedding(file_obj)
    file_obj.seek(0)
    caption_en = generate_caption(file_obj)
    caption_tokens = extract_search_tokens(caption_en)

    return {
        "embedding": image_embedding,
        "caption_en": caption_en,
        "caption_tokens": caption_tokens,
    }
