from __future__ import annotations

import json
from pathlib import Path

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from web.models import Photo


User = get_user_model()
ALPHA_REGISTRATION_CLOSED_MESSAGE = "Регистрация на альфа-тест новых пользователей временно не производится."
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


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
        "createdAt": photo.created_at.isoformat(),
    }


@ensure_csrf_cookie
def index(request: HttpRequest):
    return render(request, "index.html")


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

    created_photos: list[Photo] = []
    with transaction.atomic():
        for uploaded_file in uploaded_files:
            photo = Photo(
                user=request.user,
                original_filename=uploaded_file.name,
                file_extension=Path(uploaded_file.name).suffix.lower(),
                mime_type=getattr(uploaded_file, "content_type", "") or "",
                file_size_bytes=uploaded_file.size,
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
