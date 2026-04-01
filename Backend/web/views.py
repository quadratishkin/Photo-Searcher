from __future__ import annotations

import json
import logging
import math
import platform
import re
import socket
import sys
from pathlib import Path

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from CoreAI.runtime import (
    create_photo_index,
    create_text_embedding,
    get_ai_module_status,
    get_embedding_engine_metadata,
    rewrite_search_query,
    translate_text_to_english,
)
from web.models import DetectedFace, Person, Photo
from web.people import (
    clear_photo_faces,
    cluster_user_faces,
    describe_face_for_user,
    index_photo_faces,
    list_face_map_for_user,
    list_people_for_user,
    list_person_photos,
)
from web.services import (
    delete_photo_for_user,
    get_person_photos_payload_for_user,
    list_people_payload_for_user,
    list_photos_for_user,
    rename_person_for_user,
    search_photos_for_user,
    upload_photo_files_for_user,
)


User = get_user_model()
ALPHA_REGISTRATION_CLOSED_MESSAGE = "Регистрация на альфа-тест новых пользователей временно не производится."
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
SEARCH_RESULTS_LIMIT = 10
CAPTION_SCORE_WEIGHT = 0.22
EMBEDDING_SCORE_WEIGHT = 0.72
TOKEN_BONUS_WEIGHT = 0.06
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
QUERY_STOP_WORDS = {
    "a",
    "an",
    "and",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "near",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}
logger = logging.getLogger("liquid_photos.search")


def parse_json_body(request: HttpRequest) -> dict:
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}


def require_authenticated_user(request: HttpRequest) -> JsonResponse | None:
    if request.user.is_authenticated and request.user.is_active:
        return None
    if request.user.is_authenticated and not request.user.is_active:
        logout(request)
        return JsonResponse({"message": "Аккаунт заблокирован администратором."}, status=403)
    return JsonResponse({"message": "Требуется авторизация."}, status=401)


def require_admin_user(request: HttpRequest) -> JsonResponse | None:
    auth_error = require_authenticated_user(request)
    if auth_error is not None:
        return auth_error
    if request.user.is_staff or request.user.is_superuser:
        return None
    return JsonResponse({"message": "Доступно только администраторам."}, status=403)


def serialize_auth_user(user) -> dict:
    return {
        "id": user.id,
        "username": user.get_username(),
        "isStaff": bool(user.is_staff),
        "isSuperuser": bool(user.is_superuser),
    }


def build_loaded_model_cards(ai_status_payload: dict[str, str | bool]) -> list[dict[str, str]]:
    model_cards: list[dict[str, str]] = []

    try:
        embedding_metadata = get_embedding_engine_metadata()
    except Exception as exc:
        embedding_metadata = None
        model_cards.append(
            {
                "title": "Embedding runtime",
                "value": "Не удалось прочитать",
                "details": str(exc),
            }
        )
    else:
        model_cards.append(
            {
                "title": "Embedding runtime",
                "value": str(embedding_metadata.get("model_name", "Не указан")),
                "details": (
                    f"{embedding_metadata.get('pretrained_tag', 'no-tag')} • "
                    f"{embedding_metadata.get('device', 'unknown')} • "
                    f"{embedding_metadata.get('embedding_dimension', 0)} dim"
                ),
            }
        )

    recent_photo = (
        Photo.objects.filter(Q(caption_model__gt="") | Q(embedding_model__gt=""))
        .only("caption_model", "embedding_model", "embedding_pretrained_tag")
        .order_by("-updated_at")
        .first()
    )
    if recent_photo is not None:
        model_cards.append(
            {
                "title": "Photo indexing",
                "value": recent_photo.caption_model or recent_photo.embedding_model or "Нет данных",
                "details": (
                    recent_photo.embedding_model
                    if recent_photo.caption_model and recent_photo.embedding_model != recent_photo.caption_model
                    else recent_photo.embedding_pretrained_tag or "Модель взята из последних проиндексированных фото"
                ),
            }
        )

    recent_face = (
        DetectedFace.objects.exclude(embedding_model="")
        .only("embedding_model", "embedding_dimension")
        .order_by("-updated_at")
        .first()
    )
    if recent_face is not None:
        model_cards.append(
            {
                "title": "Face clustering",
                "value": recent_face.embedding_model or "Нет данных",
                "details": f"{recent_face.embedding_dimension} dim",
            }
        )

    model_cards.append(
        {
            "title": "AI runtime state",
            "value": str(ai_status_payload.get("summary", "Нет данных")),
            "details": str(ai_status_payload.get("details", "")),
        }
    )

    return model_cards


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
        "embeddingPretrainedTag": photo.embedding_pretrained_tag,
        "embeddingCreatedAt": photo.embedding_created_at.isoformat() if photo.embedding_created_at else "",
        "captionModel": photo.caption_model,
        "captionEn": photo.caption_en,
        "captionRu": photo.caption_ru,
        "captionRuSynonyms": list(photo.caption_ru_synonyms),
        "captionCreatedAt": photo.caption_created_at.isoformat() if photo.caption_created_at else "",
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
        if len(token) <= 1 or token in QUERY_STOP_WORDS or token in seen_tokens:
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


def normalize_person_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def find_person_match(user, query: str) -> tuple[Person | None, str]:
    normalized_query = normalize_person_name(query)
    if not normalized_query:
        return None, query.strip()

    best_match: Person | None = None
    best_span: tuple[int, int] | None = None
    best_name_length = -1

    for person in Person.objects.filter(user=user).exclude(display_name="").only("id", "display_name"):
        display_name = str(person.display_name).strip()
        normalized_name = normalize_person_name(display_name)
        if not normalized_name:
            continue

        pattern = re.compile(rf"(?<!\w){re.escape(normalized_name)}(?!\w)")
        match = pattern.search(normalized_query)
        if match is None:
            continue

        if len(normalized_name) > best_name_length:
            best_match = person
            best_span = match.span()
            best_name_length = len(normalized_name)

    if best_match is None or best_span is None:
        return None, query.strip()

    query_without_name = normalize_person_name(
        f"{normalized_query[: best_span[0]]} {normalized_query[best_span[1] :]}"
    )
    return best_match, query_without_name


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
    if not request.user.is_active:
        logout(request)
        return JsonResponse({"authenticated": False, "message": "Аккаунт заблокирован."}, status=403)

    return JsonResponse(
        {
            "authenticated": True,
            "user": serialize_auth_user(request.user),
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
            "user": serialize_auth_user(user),
        }
    )


@require_POST
def auth_logout(request: HttpRequest) -> JsonResponse:
    logout(request)
    return JsonResponse({"authenticated": False})


@require_GET
def admin_overview(request: HttpRequest) -> JsonResponse:
    admin_error = require_admin_user(request)
    if admin_error is not None:
        return admin_error

    ai_status_payload = get_ai_module_status()

    users = (
        User.objects.order_by("username")
        .annotate(
            photo_count=Count("photos", distinct=True),
            person_count=Count("people", distinct=True),
            face_count=Count("photos__detected_faces", distinct=True),
        )
    )

    user_payload = [
        {
            "id": account.id,
            "username": account.get_username(),
            "isActive": bool(account.is_active),
            "isStaff": bool(account.is_staff),
            "isSuperuser": bool(account.is_superuser),
            "dateJoined": account.date_joined.isoformat() if getattr(account, "date_joined", None) else "",
            "lastLogin": account.last_login.isoformat() if account.last_login else "",
            "photoCount": account.photo_count,
            "personCount": account.person_count,
            "faceCount": account.face_count,
        }
        for account in users
    ]

    summary = {
        "totalUsers": User.objects.count(),
        "activeUsers": User.objects.filter(is_active=True).count(),
        "bannedUsers": User.objects.filter(is_active=False).count(),
        "staffUsers": User.objects.filter(is_staff=True).count(),
        "totalPhotos": Photo.objects.count(),
        "indexedPhotos": Photo.objects.filter(processing_status="indexed").count(),
        "processingPhotos": Photo.objects.filter(processing_status="processing").count(),
        "failedPhotos": Photo.objects.filter(processing_status="failed").count(),
        "totalPeople": Person.objects.count(),
        "totalFaces": DetectedFace.objects.count(),
    }

    return JsonResponse(
        {
            "viewer": serialize_auth_user(request.user),
            "summary": summary,
            "host": {
                "hostname": socket.gethostname(),
                "platform": platform.platform(),
                "python": sys.version.split()[0],
                "timezone": str(timezone.get_current_timezone()),
                "serverTime": timezone.now().isoformat(),
            },
            "runtime": {
                "enabled": bool(ai_status_payload.get("enabled")),
                "state": str(ai_status_payload.get("state", "")),
                "summary": str(ai_status_payload.get("summary", "")),
                "details": str(ai_status_payload.get("details", "")),
                "reason": str(ai_status_payload.get("reason", "")),
                "models": build_loaded_model_cards(ai_status_payload),
            },
            "users": user_payload,
        }
    )


@require_POST
def admin_user_access(request: HttpRequest, user_id: int) -> JsonResponse:
    admin_error = require_admin_user(request)
    if admin_error is not None:
        return admin_error

    payload = parse_json_body(request)
    next_active = payload.get("active")
    if not isinstance(next_active, bool):
        return JsonResponse({"message": "Поле active должно быть булевым."}, status=400)

    try:
        target_user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({"message": "Пользователь не найден."}, status=404)

    if target_user.pk == request.user.pk and next_active is False:
        return JsonResponse({"message": "Нельзя заблокировать собственный аккаунт."}, status=400)

    if target_user.is_superuser and not request.user.is_superuser:
        return JsonResponse({"message": "Только суперпользователь может менять статус другого администратора."}, status=403)

    if target_user.is_active == next_active:
        return JsonResponse(
            {
                "message": "Статус пользователя уже актуален.",
                "user": {
                    "id": target_user.id,
                    "isActive": bool(target_user.is_active),
                },
            }
        )

    target_user.is_active = next_active
    target_user.save(update_fields=["is_active"])

    return JsonResponse(
        {
            "message": "Доступ пользователя обновлён." if next_active else "Пользователь заблокирован.",
            "user": {
                "id": target_user.id,
                "isActive": bool(target_user.is_active),
            },
        }
    )


@require_GET
def photo_list(request: HttpRequest) -> JsonResponse:
    auth_error = require_authenticated_user(request)
    if auth_error is not None:
        return auth_error

    return JsonResponse({"photos": list_photos_for_user(request.user)})


@require_GET
def people_list(request: HttpRequest) -> JsonResponse:
    auth_error = require_authenticated_user(request)
    if auth_error is not None:
        return auth_error

    return JsonResponse(list_people_payload_for_user(request.user))


@require_GET
def person_photos(request: HttpRequest, person_id: int) -> JsonResponse:
    auth_error = require_authenticated_user(request)
    if auth_error is not None:
        return auth_error

    try:
        payload = get_person_photos_payload_for_user(request.user, person_id)
    except LookupError:
        return JsonResponse({"message": "Человек не найден."}, status=404)
    return JsonResponse(payload)


@require_GET
def people_face_map(request: HttpRequest) -> JsonResponse:
    auth_error = require_authenticated_user(request)
    if auth_error is not None:
        return auth_error

    return JsonResponse(list_face_map_for_user(request.user))


@require_GET
def people_face_analysis(request: HttpRequest, face_id: int) -> JsonResponse:
    auth_error = require_authenticated_user(request)
    if auth_error is not None:
        return auth_error

    payload = describe_face_for_user(request.user, face_id)
    if payload is None:
        return JsonResponse({"message": "Лицо не найдено."}, status=404)
    return JsonResponse(payload)


@require_POST
def person_rename(request: HttpRequest, person_id: int) -> JsonResponse:
    auth_error = require_authenticated_user(request)
    if auth_error is not None:
        return auth_error

    payload = parse_json_body(request)
    try:
        response_payload = rename_person_for_user(request.user, person_id, str(payload.get("displayName", "")))
    except LookupError:
        return JsonResponse({"message": "Человек не найден."}, status=404)
    except ValueError as exc:
        return JsonResponse({"message": "Имя человека должно быть не длиннее 120 символов."}, status=400)
    return JsonResponse(response_payload)


@require_POST
def photo_search(request: HttpRequest) -> JsonResponse:
    auth_error = require_authenticated_user(request)
    if auth_error is not None:
        return auth_error

    try:
        payload = parse_json_body(request)
        response_payload = search_photos_for_user(request.user, str(payload.get("query", "")))
    except ValueError as exc:
        return JsonResponse({"message": str(exc)}, status=400)
    except Exception as exc:
        logger.exception("photo_search.failed user=%s", request.user.get_username())
        return JsonResponse(
            {"message": f"AI-модуль недоступен для поиска: {exc}"},
            status=503,
        )
    return JsonResponse(response_payload)


@require_POST
def photo_upload(request: HttpRequest) -> JsonResponse:
    auth_error = require_authenticated_user(request)
    if auth_error is not None:
        return auth_error

    try:
        response_payload = upload_photo_files_for_user(request.user, request.FILES.getlist("files"))
    except ValueError as exc:
        return JsonResponse({"message": str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse(
            {"message": f"Не удалось построить AI-индекс для загружаемых фото: {exc}"},
            status=500,
        )
    return JsonResponse(response_payload, status=201)


@require_POST
def photo_delete(request: HttpRequest, photo_id: int) -> JsonResponse:
    auth_error = require_authenticated_user(request)
    if auth_error is not None:
        return auth_error

    try:
        response_payload = delete_photo_for_user(request.user, photo_id)
    except LookupError:
        return JsonResponse({"message": "Фотография не найдена."}, status=404)
    return JsonResponse(response_payload)
