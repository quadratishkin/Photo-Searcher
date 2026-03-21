from __future__ import annotations

import json
import math
import re
from pathlib import Path

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from photo_ai import (
    create_photo_index,
    create_text_embedding,
    get_ai_module_status,
    get_embedding_engine_metadata,
    translate_text_to_english,
)
from web.models import Photo


User = get_user_model()
ALPHA_REGISTRATION_CLOSED_MESSAGE = "Регистрация на альфа-тест новых пользователей временно не производится."
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
SEARCH_RESULTS_LIMIT = 10
CAPTION_SCORE_WEIGHT = 0.35
EMBEDDING_SCORE_WEIGHT = 0.55
TOKEN_BONUS_WEIGHT = 0.10
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def parse_json_body(request: HttpRequest) -> dict:
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}


def require_authenticated_user(request: HttpRequest) -> JsonResponse | None:
    if request.user.is_authenticated:
        return None
    return JsonResponse({"message": "Требуется авторизация."}, status=401)


def serialize_photo(photo: Photo) -> dict:
    return {
        "id": photo.id,
        "url": photo.image.url,
        "originalFilename": photo.original_filename,
        "fileExtension": photo.file_extension,
        "fileSizeBytes": photo.file_size_bytes,
        "mimeType": photo.mime_type,
        "processingStatus": photo.processing_status,
        "hasEmbedding": bool(photo.embedding_dimension and photo.embedding_vector),
        "embeddingDimension": photo.embedding_dimension,
        "embeddingModel": photo.embedding_model,
        "captionEn": photo.caption_en,
        "createdAt": photo.created_at.isoformat(),
    }


def serialize_search_hit(photo: Photo, score: float) -> dict:
    normalized_score = max(0.0, min(1.0, (score + 1.0) / 2.0))
    payload = serialize_photo(photo)
    payload.update(
        {
            "score": round(score, 6),
            "scorePercent": round(normalized_score * 100, 2),
        }
    )
    return payload


def is_valid_embedding_vector(vector: object, dimension: int) -> bool:
    if not isinstance(vector, list) or len(vector) != dimension:
        return False
    return all(isinstance(value, (int, float)) and math.isfinite(float(value)) for value in vector)


def dot_product(left: list[float], right: list[float]) -> float:
    return sum(float(left_item) * float(right_item) for left_item, right_item in zip(left, right, strict=True))


def extract_query_tokens(text: str) -> list[str]:
    tokens = TOKEN_PATTERN.findall(text.strip().lower())
    unique_tokens: list[str] = []
    seen_tokens: set[str] = set()
    for token in tokens:
        if len(token) <= 1 or token in seen_tokens:
            continue
        seen_tokens.add(token)
        unique_tokens.append(token)
    return unique_tokens


def score_caption_match(query_tokens: list[str], caption_tokens: object) -> tuple[float, float]:
    if not query_tokens or not isinstance(caption_tokens, list):
        return 0.0, 0.0

    normalized_caption_tokens = {
        str(token).strip().lower()
        for token in caption_tokens
        if isinstance(token, str) and str(token).strip()
    }
    if not normalized_caption_tokens:
        return 0.0, 0.0

    matched_tokens = [token for token in query_tokens if token in normalized_caption_tokens]
    if not matched_tokens:
        return 0.0, 0.0

    match_ratio = len(matched_tokens) / len(query_tokens)
    token_bonus = min(1.0, len(matched_tokens) / max(3, len(normalized_caption_tokens)))
    return match_ratio, token_bonus


@ensure_csrf_cookie
def index(request: HttpRequest):
    return render(request, "index.html")


@require_GET
def ai_status(request: HttpRequest) -> JsonResponse:
    return JsonResponse(get_ai_module_status())


@require_GET
def auth_me(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False}, status=401)

    return JsonResponse(
        {
            "authenticated": True,
            "user": {
                "id": request.user.id,
                "username": request.user.get_username(),
            },
        }
    )


@require_POST
def auth_register(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"message": ALPHA_REGISTRATION_CLOSED_MESSAGE}, status=403)


@require_POST
def auth_login(request: HttpRequest) -> JsonResponse:
    payload = parse_json_body(request)
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))

    if not username or not password:
        return JsonResponse({"message": "Введите имя пользователя и пароль."}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"message": "Неверное имя пользователя или пароль."}, status=400)

    login(request, user)
    return JsonResponse(
        {
            "authenticated": True,
            "user": {
                "id": user.id,
                "username": user.get_username(),
            },
        }
    )


@require_POST
def auth_logout(request: HttpRequest) -> JsonResponse:
    logout(request)
    return JsonResponse({"authenticated": False})


@require_GET
def photo_list(request: HttpRequest) -> JsonResponse:
    auth_error = require_authenticated_user(request)
    if auth_error is not None:
        return auth_error

    photos = [serialize_photo(photo) for photo in Photo.objects.filter(user=request.user)]
    return JsonResponse({"photos": photos})


@require_POST
def photo_search(request: HttpRequest) -> JsonResponse:
    auth_error = require_authenticated_user(request)
    if auth_error is not None:
        return auth_error

    payload = parse_json_body(request)
    query = str(payload.get("query", "")).strip()
    if not query:
        return JsonResponse({"message": "Введите текстовый запрос для поиска."}, status=400)

    try:
        engine_metadata = get_embedding_engine_metadata()
    except Exception as exc:
        return JsonResponse(
            {"message": f"AI-модуль недоступен для поиска: {exc}"},
            status=503,
        )

    expected_model_name = str(engine_metadata["model_name"])
    expected_pretrained_tag = str(engine_metadata["pretrained_tag"])
    expected_dimension = int(engine_metadata["embedding_dimension"])
    try:
        translated_query = translate_text_to_english(query)
    except Exception:
        translated_query = query.strip().lower()

    combined_query_text = f"{query.strip()} {translated_query}".strip()
    english_query_tokens = extract_query_tokens(translated_query)

    indexed_photos = list(
        Photo.objects.filter(user=request.user, embedding_dimension__gt=0)
        .only(
            "id",
            "image",
            "original_filename",
            "file_extension",
            "mime_type",
            "file_size_bytes",
            "processing_status",
            "created_at",
            "embedding_model",
            "embedding_pretrained_tag",
            "embedding_dimension",
            "embedding_vector",
            "caption_en",
            "caption_tokens",
        )
    )
    if not indexed_photos:
        return JsonResponse(
            {
                "query": query,
                "photos": [],
                "totalIndexedPhotos": 0,
                "message": "В вашей медиатеке пока нет проиндексированных фото для семантического поиска.",
            }
        )

    try:
        text_embedding = create_text_embedding(combined_query_text)
    except ValueError as exc:
        return JsonResponse({"message": str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse(
            {"message": f"Не удалось построить embedding для текстового запроса: {exc}"},
            status=500,
        )

    query_vector = list(text_embedding["vector"])
    search_hits: list[tuple[float, Photo, dict[str, float | str]]] = []
    skipped_photos = 0

    for photo in indexed_photos:
        if photo.embedding_model != expected_model_name:
            skipped_photos += 1
            continue
        if photo.embedding_pretrained_tag != expected_pretrained_tag:
            skipped_photos += 1
            continue
        if photo.embedding_dimension != expected_dimension:
            skipped_photos += 1
            continue
        if not is_valid_embedding_vector(photo.embedding_vector, expected_dimension):
            skipped_photos += 1
            continue

        similarity = dot_product(query_vector, photo.embedding_vector)
        caption_match_ratio, token_bonus = score_caption_match(english_query_tokens, photo.caption_tokens)
        hybrid_score = (
            (similarity * EMBEDDING_SCORE_WEIGHT)
            + (caption_match_ratio * CAPTION_SCORE_WEIGHT)
            + (token_bonus * TOKEN_BONUS_WEIGHT)
        )
        debug_meta = {
            "embeddingScore": round(similarity, 6),
            "captionScore": round(caption_match_ratio, 6),
            "tokenBonus": round(token_bonus, 6),
            "translatedQuery": translated_query,
        }
        search_hits.append((hybrid_score, photo, debug_meta))

    if not search_hits:
        return JsonResponse(
            {
                "query": query,
                "photos": [],
                "totalIndexedPhotos": len(indexed_photos),
                "skippedPhotos": skipped_photos,
                "message": "Не найдено ни одного фото с валидным embedding-индексом для текущей AI-модели.",
            }
        )

    search_hits.sort(key=lambda item: item[0], reverse=True)
    top_hits = search_hits[:SEARCH_RESULTS_LIMIT]

    return JsonResponse(
        {
            "query": query,
            "translatedQuery": translated_query,
            "photos": [
                {**serialize_search_hit(photo, score), **debug_meta}
                for score, photo, debug_meta in top_hits
            ],
            "topK": SEARCH_RESULTS_LIMIT,
            "totalIndexedPhotos": len(indexed_photos),
            "skippedPhotos": skipped_photos,
            "message": "" if top_hits else "Совпадений не найдено.",
        }
    )


@require_POST
def photo_upload(request: HttpRequest) -> JsonResponse:
    auth_error = require_authenticated_user(request)
    if auth_error is not None:
        return auth_error

    uploaded_files = request.FILES.getlist("files")
    if not uploaded_files:
        return JsonResponse({"message": "Не выбраны файлы для загрузки."}, status=400)

    invalid_files = [
        uploaded_file.name
        for uploaded_file in uploaded_files
        if Path(uploaded_file.name).suffix.lower() not in ALLOWED_PHOTO_EXTENSIONS
    ]
    if invalid_files:
        return JsonResponse(
            {
                "message": "Можно загружать только изображения поддерживаемых форматов.",
                "invalidFiles": invalid_files,
            },
            status=400,
        )

    indexed_uploads: list[tuple] = []
    try:
        for uploaded_file in uploaded_files:
            uploaded_file.seek(0)
            photo_index = create_photo_index(uploaded_file)
            uploaded_file.seek(0)
            indexed_uploads.append((uploaded_file, photo_index))
    except Exception as exc:
        return JsonResponse(
            {"message": f"Не удалось построить AI-индекс для загружаемых фото: {exc}"},
            status=500,
        )

    created_photos: list[Photo] = []
    with transaction.atomic():
        for uploaded_file, photo_index in indexed_uploads:
            embedding_result = photo_index["embedding"]
            photo = Photo(
                user=request.user,
                original_filename=uploaded_file.name,
                file_extension=Path(uploaded_file.name).suffix.lower(),
                mime_type=getattr(uploaded_file, "content_type", "") or "",
                file_size_bytes=uploaded_file.size,
                processing_status="indexed",
                embedding_model=str(embedding_result["model_name"]),
                embedding_pretrained_tag=str(embedding_result["pretrained_tag"]),
                embedding_dimension=int(embedding_result["dimension"]),
                embedding_vector=list(embedding_result["vector"]),
                embedding_created_at=timezone.now(),
                caption_model="Salesforce/blip-image-captioning-base",
                caption_en=str(photo_index["caption_en"]),
                caption_tokens=list(photo_index["caption_tokens"]),
                caption_created_at=timezone.now(),
            )
            photo.image.save(uploaded_file.name, uploaded_file, save=False)
            photo.save()
            created_photos.append(photo)

    return JsonResponse(
        {
            "message": f"Загружено {len(created_photos)} фото.",
            "photos": [serialize_photo(photo) for photo in created_photos],
        },
        status=201,
    )


@require_POST
def photo_delete(request: HttpRequest, photo_id: int) -> JsonResponse:
    auth_error = require_authenticated_user(request)
    if auth_error is not None:
        return auth_error

    try:
        photo = Photo.objects.get(id=photo_id, user=request.user)
    except Photo.DoesNotExist:
        return JsonResponse({"message": "Фотография не найдена."}, status=404)

    photo.image.delete(save=False)
    photo.delete()
    return JsonResponse({"message": "Фотография удалена.", "photoId": photo_id})
