from __future__ import annotations

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from web.models import DetectedFace, Person, Photo, TelegramProfile


User = get_user_model()


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "original_filename", "processing_status", "embedding_model", "created_at")
    list_filter = ("processing_status", "embedding_model", "caption_model", "created_at")
    search_fields = ("original_filename", "user__username", "caption_ru", "caption_en")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at", "embedding_created_at", "caption_created_at")


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("id", "display_name", "user", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("display_name", "user__username")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(DetectedFace)
class DetectedFaceAdmin(admin.ModelAdmin):
    list_display = ("id", "photo", "person", "embedding_model", "quality_score", "detection_score", "created_at")
    list_filter = ("embedding_model", "created_at")
    search_fields = ("photo__original_filename", "photo__user__username", "person__display_name")
    autocomplete_fields = ("photo", "person")
    readonly_fields = ("created_at", "updated_at", "embedding_created_at")


@admin.register(TelegramProfile)
class TelegramProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "telegram_username", "telegram_user_id", "telegram_chat_id", "created_at")
    search_fields = ("user__username", "telegram_username", "telegram_first_name", "telegram_last_name")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "is_active", "is_staff", "is_superuser", "date_joined", "last_login")
    list_filter = ("is_active", "is_staff", "is_superuser", "date_joined")
