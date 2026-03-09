from __future__ import annotations

import json

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST


User = get_user_model()


def parse_json_body(request: HttpRequest) -> dict:
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}


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
    payload = parse_json_body(request)
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    password_confirm = str(payload.get("passwordConfirm", ""))

    field_errors: dict[str, str] = {}

    if len(username) < 3:
        field_errors["username"] = "Имя пользователя должно быть не короче 3 символов."
    elif User.objects.filter(username=username).exists():
        field_errors["username"] = "Пользователь с таким именем уже существует."

    if len(password) < 8:
        field_errors["password"] = "Пароль должен содержать не меньше 8 символов."
    elif password != password_confirm:
        field_errors["passwordConfirm"] = "Пароли не совпадают."

    if field_errors:
        return JsonResponse({"message": "Проверьте поля формы.", "fieldErrors": field_errors}, status=400)

    user = User(username=username)
    try:
        validate_password(password, user=user)
    except ValidationError as error:
        return JsonResponse(
            {
                "message": "Пароль не прошёл проверку.",
                "fieldErrors": {"password": error.messages[0]},
            },
            status=400,
        )

    user = User.objects.create_user(username=username, password=password)
    login(request, user)
    return JsonResponse(
        {
            "authenticated": True,
            "user": {
                "id": user.id,
                "username": user.get_username(),
            },
        },
        status=201,
    )


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
