from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve

from web.views import auth_login, auth_logout, auth_me, auth_register, index, photo_list, photo_upload


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", index, name="index"),
    path("api/auth/me", auth_me, name="auth-me"),
    path("api/auth/login", auth_login, name="auth-login"),
    path("api/auth/register", auth_register, name="auth-register"),
    path("api/auth/logout", auth_logout, name="auth-logout"),
    path("api/photos", photo_list, name="photo-list"),
    path("api/photos/upload", photo_upload, name="photo-upload"),
]

if settings.DEBUG:
    urlpatterns += [
        re_path(r"^demo/(?P<path>.*)$", serve, {"document_root": settings.BASE_DIR / "public" / "demo"}),
    ]
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
