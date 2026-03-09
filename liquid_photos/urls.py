from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve

from web.views import index


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", index, name="index"),
]

if settings.DEBUG:
    urlpatterns += [
        re_path(r"^demo/(?P<path>.*)$", serve, {"document_root": settings.BASE_DIR / "public" / "demo"}),
    ]
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
