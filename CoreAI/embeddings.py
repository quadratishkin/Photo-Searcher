from __future__ import annotations

import re
import json
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from threading import Lock
from typing import BinaryIO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_NAME = "ViT-B-32"
DEFAULT_PRETRAINED_TAG = "laion2b_s34b_b79k"
DEFAULT_CAPTION_MODEL_NAME = "Salesforce/blip-image-captioning-base"
DEFAULT_TRANSLATION_MODEL_NAME = "Helsinki-NLP/opus-mt-ru-en"
DEFAULT_COMPUTE_DEVICE = "auto"
DEFAULT_QUERY_REWRITE_ENABLED = False
DEFAULT_QUERY_REWRITE_MODEL_PATH = "CoreAI/Models/query-rewriter/Qwen2.5-1.5B-Instruct-4bit"
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
RUSSIAN_TOKEN_PATTERN = re.compile(r"[a-zа-яё0-9-]+", re.IGNORECASE)
JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)
QUERY_REWRITE_SYSTEM_PROMPT = """You normalize noisy Russian photo-search queries.
Rules:
1. Fix only obvious typos, punctuation, spacing, and inflection mistakes.
2. Preserve meaning exactly.
3. Never replace a word with a synonym, a more generic word, slang normalization, or a different object.
4. Never add details not present in the query.
5. Keep ambiguity if the query is ambiguous.
6. Return strict JSON only with keys normalized_ru, normalized_en, search_prompt_en.
7. search_prompt_en must be a short English visual search query, not a full explanation.
8. Keep person references like "я" only if they were already present in the query.
9. If the Russian query is already valid, keep normalized_ru unchanged.
Examples:
Input: чел с сабакой на пляжи
Output: {"normalized_ru":"чел с собакой на пляже","normalized_en":"guy with a dog on the beach","search_prompt_en":"guy with a dog on the beach"}
Input: какой то закатик у воды
Output: {"normalized_ru":"какой-то закатик у воды","normalized_en":"sunset by the water","search_prompt_en":"sunset by the water"}
Input: девка в очках возле тачки на море
Output: {"normalized_ru":"девка в очках возле тачки на море","normalized_en":"woman in glasses near a car by the sea","search_prompt_en":"woman in glasses near a car by the sea"}
Input: Госпожа
Output: {"normalized_ru":"Госпожа","normalized_en":"madam","search_prompt_en":"madam"}
"""


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
    device: str


@dataclass(frozen=True)
class RuntimeConfig:
    model_name: str
    pretrained_tag: str
    caption_model_name: str
    translation_model_name: str
    compute_device: str
    query_rewrite_enabled: bool
    query_rewrite_model_path: str


@dataclass(frozen=True)
class QueryRewriteBundle:
    model: object
    tokenizer: object
    model_path: str


@dataclass(frozen=True)
class QueryRewriteResult:
    original_query: str
    normalized_ru: str
    normalized_en: str
    search_prompt_en: str
    used_rewriter: bool
    fallback_reason: str


_model_bundle: ModelBundle | None = None
_model_lock = Lock()
_caption_bundle: CaptionBundle | None = None
_caption_lock = Lock()
_translation_bundle: TranslationBundle | None = None
_translation_lock = Lock()
_query_rewrite_bundle: QueryRewriteBundle | None = None
_query_rewrite_lock = Lock()
_runtime_status = RuntimeStatus(
    state="idle",
    summary="OpenCLIP не загружен",
    details="Модель будет поднята при первой загрузке фото",
    reason="Ленивая инициализация для server-side embedding pipeline.",
)
_runtime_config = RuntimeConfig(
    model_name=DEFAULT_MODEL_NAME,
    pretrained_tag=DEFAULT_PRETRAINED_TAG,
    caption_model_name=DEFAULT_CAPTION_MODEL_NAME,
    translation_model_name=DEFAULT_TRANSLATION_MODEL_NAME,
    compute_device=DEFAULT_COMPUTE_DEVICE,
    query_rewrite_enabled=DEFAULT_QUERY_REWRITE_ENABLED,
    query_rewrite_model_path=DEFAULT_QUERY_REWRITE_MODEL_PATH,
)


def _resolve_project_path(value: str) -> str:
    stripped_value = value.strip()
    if not stripped_value:
        return stripped_value

    candidate_path = Path(stripped_value).expanduser()
    if candidate_path.is_absolute():
        return str(candidate_path)

    project_candidate = (PROJECT_ROOT / candidate_path).resolve()
    if project_candidate.exists():
        return str(project_candidate)

    return stripped_value


def _normalize_runtime_config(config: dict[str, str] | None) -> RuntimeConfig:
    source = config or {}
    compute_device = str(source.get("sComputeDevice", DEFAULT_COMPUTE_DEVICE)).strip().lower() or DEFAULT_COMPUTE_DEVICE
    if compute_device not in {"auto", "cuda", "mps", "cpu"}:
        compute_device = DEFAULT_COMPUTE_DEVICE

    query_rewrite_enabled = (str(source.get("bEnableQueryRewrite", DEFAULT_QUERY_REWRITE_ENABLED)).strip().lower()
        in {"1", "true", "yes", "on"})
    model_name = str(source.get("sOpenClipModelName", DEFAULT_MODEL_NAME)).strip() or DEFAULT_MODEL_NAME
    pretrained_tag = str(source.get("sOpenClipPretrained", DEFAULT_PRETRAINED_TAG)).strip() or DEFAULT_PRETRAINED_TAG
    caption_model_name = str(source.get("sCaptionModelName", DEFAULT_CAPTION_MODEL_NAME)).strip() or DEFAULT_CAPTION_MODEL_NAME
    translation_model_name = (
        str(source.get("sTranslationModelName", DEFAULT_TRANSLATION_MODEL_NAME)).strip()
        or DEFAULT_TRANSLATION_MODEL_NAME
    )
    query_rewrite_model_path = (
        str(source.get("sQueryRewriteModelPath", DEFAULT_QUERY_REWRITE_MODEL_PATH)).strip()
        or DEFAULT_QUERY_REWRITE_MODEL_PATH
    )

    return RuntimeConfig(
        model_name=model_name,
        pretrained_tag=_resolve_project_path(pretrained_tag),
        caption_model_name=_resolve_project_path(caption_model_name),
        translation_model_name=_resolve_project_path(translation_model_name),
        compute_device=compute_device,
        query_rewrite_enabled=query_rewrite_enabled,
        query_rewrite_model_path=_resolve_project_path(query_rewrite_model_path),
    )


def _reset_runtime_state(reason: str) -> None:
    global _model_bundle, _caption_bundle, _translation_bundle, _query_rewrite_bundle, _runtime_status

    _model_bundle = None
    _caption_bundle = None
    _translation_bundle = None
    _query_rewrite_bundle = None
    _runtime_status = RuntimeStatus(
        state="idle",
        summary="AI runtime перенастроен",
        details="Модели будут загружены заново при следующем запросе",
        reason=reason,
    )


def configure_runtime(config: dict[str, str] | None = None) -> dict[str, str]:
    global _runtime_config

    normalized_config = _normalize_runtime_config(config)
    with _model_lock, _caption_lock, _translation_lock, _query_rewrite_lock:
        if normalized_config != _runtime_config:
            _runtime_config = normalized_config
            _reset_runtime_state("Изменились параметры модели или устройства вычислений.")
    return asdict(_runtime_config)


def _detect_device() -> str:
    import torch

    requested_device = _runtime_config.compute_device
    has_cuda = torch.cuda.is_available()
    has_mps = bool(getattr(torch.backends, "mps", None)) and torch.backends.mps.is_built() and torch.backends.mps.is_available()

    if requested_device == "auto":
        if has_cuda:
            return "cuda"
        if has_mps:
            return "mps"
        return "cpu"

    if requested_device == "cuda":
        if not has_cuda:
            raise RuntimeError("В CoreAI.config выбран CUDA, но он недоступен на текущем устройстве.")
        return "cuda"

    if requested_device == "mps":
        if not has_mps:
            raise RuntimeError("В CoreAI.config выбран MPS, но PyTorch MPS недоступен на текущем устройстве.")
        return "mps"

    return "cpu"


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
            _runtime_config.model_name,
            pretrained=_runtime_config.pretrained_tag,
            device=device,
        )
        model.eval()

        image_size = getattr(getattr(model, "visual", None), "image_size", 224)
        if isinstance(image_size, tuple):
            probe_height, probe_width = image_size
        else:
            probe_height = int(image_size)
            probe_width = int(image_size)

        with torch.no_grad():
            probe = torch.zeros((1, 3, probe_height, probe_width), device=device)
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
            summary="AI retrieval активен",
            details=f"{_runtime_config.model_name} / {_runtime_config.pretrained_tag} / {device}",
            reason="Embedding и hybrid search pipeline готовы к обработке новых фото и запросов.",
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
        processor = BlipProcessor.from_pretrained(_runtime_config.caption_model_name)
        model = BlipForConditionalGeneration.from_pretrained(_runtime_config.caption_model_name).to(device)
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

        device = _detect_device()
        tokenizer = AutoTokenizer.from_pretrained(_runtime_config.translation_model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(_runtime_config.translation_model_name).to(device)
        model.eval()

        _translation_bundle = TranslationBundle(tokenizer=tokenizer, model=model, device=device)
        return _translation_bundle


def _load_query_rewrite_bundle() -> QueryRewriteBundle:
    global _query_rewrite_bundle

    with _query_rewrite_lock:
        if _query_rewrite_bundle is not None:
            return _query_rewrite_bundle

        if not _runtime_config.query_rewrite_enabled:
            raise RuntimeError("Query rewriter отключён в конфиге.")

        try:
            from mlx_lm import load
        except ImportError as exc:
            raise RuntimeError("MLX query rewriter зависимости не установлены.") from exc

        model_path = _runtime_config.query_rewrite_model_path
        if not model_path:
            raise RuntimeError("В CoreAI.config не указан путь к query rewrite модели.")
        if not Path(model_path).exists():
            raise RuntimeError(f"Не найдена query rewrite модель: {model_path}")

        model, tokenizer = load(model_path)
        _query_rewrite_bundle = QueryRewriteBundle(model=model, tokenizer=tokenizer, model_path=model_path)
        return _query_rewrite_bundle


def normalize_english_text(text: str) -> str:
    normalized = text.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def normalize_russian_text(text: str) -> str:
    normalized = text.strip()
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
        model_name=_runtime_config.model_name,
        pretrained_tag=_runtime_config.pretrained_tag,
        device=bundle.device,
        embedding_dimension=bundle.embedding_dimension,
    )
    return asdict(metadata)


def get_runtime_status() -> dict[str, str]:
    return asdict(_runtime_status)


def warm_runtime() -> dict[str, str]:
    global _runtime_status

    bundle = _load_model_bundle()
    rewrite_details = "query rewrite: disabled"
    if _runtime_config.query_rewrite_enabled:
        try:
            rewrite_bundle = _load_query_rewrite_bundle()
            rewrite_details = f"query rewrite: {Path(rewrite_bundle.model_path).name}"
        except Exception as exc:
            rewrite_details = f"query rewrite fallback: {exc}"

    _runtime_status = RuntimeStatus(
        state="ready",
        summary="AI retrieval активен",
        details=f"{_runtime_config.model_name} / {_runtime_config.pretrained_tag} / {bundle.device} / {rewrite_details}",
        reason="Embedding pipeline и query rewrite runtime готовы к поисковым запросам.",
    )
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
        "model_name": _runtime_config.model_name,
        "pretrained_tag": _runtime_config.pretrained_tag,
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
    tokenizer = open_clip.get_tokenizer(_runtime_config.model_name)
    if hasattr(tokenizer, "tokenizer") and hasattr(tokenizer.tokenizer, "__call__"):
        context_length = getattr(tokenizer, "context_length", None) or 64
        encoded = tokenizer.tokenizer(
            [normalized_query],
            return_tensors="pt",
            max_length=context_length,
            padding="max_length",
            truncation=True,
        )
        tokens = encoded.input_ids
        sep_token_id = getattr(tokenizer.tokenizer, "sep_token_id", None)
        if getattr(tokenizer, "strip_sep_token", False) and sep_token_id is not None:
            tokens = torch.where(tokens == sep_token_id, torch.zeros_like(tokens), tokens)
        tokens = tokens.to(bundle.device)
    else:
        tokens = tokenizer([normalized_query]).to(bundle.device)

    with torch.no_grad():
        text_features = bundle.model.encode_text(tokens)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)

    vector = text_features.squeeze(0).detach().cpu().tolist()
    return {
        "model_name": _runtime_config.model_name,
        "pretrained_tag": _runtime_config.pretrained_tag,
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
    prepared_inputs = {name: value.to(bundle.device) for name, value in inputs.items()}

    with torch.no_grad():
        output_tokens = bundle.model.generate(**prepared_inputs, max_new_tokens=64)

    translated = bundle.tokenizer.decode(output_tokens[0].detach().cpu(), skip_special_tokens=True).strip()
    if not translated:
        raise RuntimeError("Не удалось перевести запрос на английский.")
    return normalize_english_text(translated)


def _extract_json_object(raw_text: str) -> dict[str, str]:
    stripped = raw_text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        stripped = stripped.replace("json\n", "", 1).strip()

    match = JSON_OBJECT_PATTERN.search(stripped)
    if not match:
        raise ValueError("LLM не вернула JSON-объект.")

    payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("LLM вернула не JSON-объект.")
    return {str(key): str(value).strip() for key, value in payload.items()}


def _tokenize_russian_text(text: str) -> list[str]:
    return [token.lower() for token in RUSSIAN_TOKEN_PATTERN.findall(normalize_russian_text(text))]


def _is_safe_russian_rewrite(original: str, candidate: str) -> bool:
    normalized_original = normalize_russian_text(original)
    normalized_candidate = normalize_russian_text(candidate)
    if normalized_candidate == normalized_original:
        return True

    original_tokens = _tokenize_russian_text(normalized_original)
    candidate_tokens = _tokenize_russian_text(normalized_candidate)
    if not original_tokens or len(original_tokens) != len(candidate_tokens):
        return False

    for left, right in zip(original_tokens, candidate_tokens, strict=True):
        if SequenceMatcher(None, left, right).ratio() < 0.72:
            return False

    return True


def rewrite_search_query(query: str) -> dict[str, str | bool]:
    normalized_query = normalize_russian_text(query)
    if not normalized_query:
        raise ValueError("Текстовый запрос не должен быть пустым.")

    if not any("а" <= char.lower() <= "я" or char.lower() == "ё" for char in normalized_query):
        normalized_en = normalize_english_text(normalized_query)
        result = QueryRewriteResult(
            original_query=normalized_query,
            normalized_ru=normalized_query,
            normalized_en=normalized_en,
            search_prompt_en=normalized_en,
            used_rewriter=False,
            fallback_reason="Запрос уже на английском или без кириллицы.",
        )
        return asdict(result)

    if not _runtime_config.query_rewrite_enabled:
        translated = translate_text_to_english(normalized_query)
        result = QueryRewriteResult(
            original_query=normalized_query,
            normalized_ru=normalized_query,
            normalized_en=translated,
            search_prompt_en=translated,
            used_rewriter=False,
            fallback_reason="Query rewriter отключён; использован обычный перевод.",
        )
        return asdict(result)

    try:
        from mlx_lm import generate
    except ImportError:
        translated = translate_text_to_english(normalized_query)
        result = QueryRewriteResult(
            original_query=normalized_query,
            normalized_ru=normalized_query,
            normalized_en=translated,
            search_prompt_en=translated,
            used_rewriter=False,
            fallback_reason="MLX query rewriter недоступен; использован обычный перевод.",
        )
        return asdict(result)

    try:
        bundle = _load_query_rewrite_bundle()
        prompt = bundle.tokenizer.apply_chat_template(
            [
                {"role": "system", "content": QUERY_REWRITE_SYSTEM_PROMPT},
                {"role": "user", "content": normalized_query},
            ],
            add_generation_prompt=True,
        )
        raw_output = generate(bundle.model, bundle.tokenizer, prompt=prompt, verbose=False, max_tokens=120)
        payload = _extract_json_object(raw_output)

        rewritten_ru = payload.get("normalized_ru", "").strip() or normalized_query
        if not _is_safe_russian_rewrite(normalized_query, rewritten_ru):
            raise ValueError("LLM попыталась заменить слова в русском запросе; использован безопасный fallback.")
        normalized_en = normalize_english_text(payload.get("normalized_en", "").strip())
        search_prompt_en = normalize_english_text(payload.get("search_prompt_en", "").strip())

        if not normalized_en or not search_prompt_en:
            raise ValueError("LLM вернула пустые english-поля.")

        result = QueryRewriteResult(
            original_query=normalized_query,
            normalized_ru=normalized_query,
            normalized_en=normalized_en,
            search_prompt_en=search_prompt_en,
            used_rewriter=True,
            fallback_reason="",
        )
        return asdict(result)
    except Exception as exc:
        translated = translate_text_to_english(normalized_query)
        result = QueryRewriteResult(
            original_query=normalized_query,
            normalized_ru=normalized_query,
            normalized_en=translated,
            search_prompt_en=translated,
            used_rewriter=False,
            fallback_reason=str(exc),
        )
        return asdict(result)


def create_photo_index(file_obj: BinaryIO) -> dict[str, object]:
    image_embedding = create_image_embedding(file_obj)
    file_obj.seek(0)
    caption_en = generate_caption(file_obj)
    caption_tokens = extract_search_tokens(caption_en)

    return {
        "embedding": image_embedding,
        "caption_model_name": _runtime_config.caption_model_name,
        "caption_en": caption_en,
        "caption_tokens": caption_tokens,
    }
