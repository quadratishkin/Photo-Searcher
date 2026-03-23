from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve

from web.views import (
    ai_status,
    auth_login,
    auth_logout,
    auth_me,
    auth_register,
    index,
    people_list,
    person_photos,
    person_rename,
    photo_delete,
    photo_list,
    photo_search,
    photo_upload,
)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", index, name="index"),
    path("api/ai/status", ai_status, name="ai-status"),
    path("api/auth/me", auth_me, name="auth-me"),
    path("api/auth/login", auth_login, name="auth-login"),
    path("api/auth/register", auth_register, name="auth-register"),
    path("api/auth/logout", auth_logout, name="auth-logout"),
    path("api/photos", photo_list, name="photo-list"),
    path("api/photos/search", photo_search, name="photo-search"),
    path("api/photos/upload", photo_upload, name="photo-upload"),
    path("api/photos/<int:photo_id>/delete", photo_delete, name="photo-delete"),
    path("api/people", people_list, name="people-list"),
    path("api/people/<int:person_id>/photos", person_photos, name="person-photos"),
    path("api/people/<int:person_id>/rename", person_rename, name="person-rename"),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += [
        re_path(r"^demo/(?P<path>.*)$", serve, {"document_root": settings.BASE_DIR / "WebUI" / "public" / "demo"}),
    ]
