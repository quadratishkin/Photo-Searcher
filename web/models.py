from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models


User = get_user_model()


def user_photo_upload_to(instance: "Photo", filename: str) -> str:
    extension = Path(filename).suffix.lower()
    stored_name = f"{uuid4().hex}{extension}"
    return f"users/{instance.user.username}/{stored_name}"


def user_face_preview_upload_to(instance: "DetectedFace", filename: str) -> str:
    extension = Path(filename).suffix.lower() or ".jpg"
    stored_name = f"{uuid4().hex}{extension}"
    return f"users/{instance.photo.user.username}/faces/{stored_name}"


class Photo(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="photos")
    image = models.FileField(upload_to=user_photo_upload_to, max_length=500)
    original_filename = models.CharField(max_length=255)
    file_extension = models.CharField(max_length=16)
    mime_type = models.CharField(max_length=120, blank=True)
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    processing_status = models.CharField(max_length=32, default="uploaded")
    embedding_model = models.CharField(max_length=80, blank=True)
    embedding_pretrained_tag = models.CharField(max_length=120, blank=True)
    embedding_dimension = models.PositiveIntegerField(default=0)
    embedding_vector = models.JSONField(default=list, blank=True)
    embedding_created_at = models.DateTimeField(null=True, blank=True)
    caption_model = models.CharField(max_length=120, blank=True)
    caption_en = models.TextField(blank=True)
    caption_tokens = models.JSONField(default=list, blank=True)
    caption_created_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user.username}: {self.original_filename}"


class Person(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="people")
    display_name = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.display_name or f"Person #{self.pk}"


class DetectedFace(models.Model):
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE, related_name="detected_faces")
    person = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL, related_name="faces")
    preview_image = models.FileField(upload_to=user_face_preview_upload_to, max_length=500, blank=True)
    bbox = models.JSONField(default=list, blank=True)
    landmarks = models.JSONField(default=list, blank=True)
    detection_score = models.FloatField(default=0.0)
    quality_score = models.FloatField(default=0.0)
    embedding_model = models.CharField(max_length=120, blank=True)
    embedding_dimension = models.PositiveIntegerField(default=0)
    embedding_vector = models.JSONField(default=list, blank=True)
    embedding_created_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-quality_score", "id"]

    def __str__(self) -> str:
        return f"Face #{self.pk} for photo #{self.photo_id}"
