from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from CoreAI.runtime import create_photo_index
from web.models import Photo


class Command(BaseCommand):
    help = "Rebuild embeddings and captions for existing uploaded photos."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--photo-id", type=int, help="Reindex only one photo by id.")
        parser.add_argument("--limit", type=int, help="Reindex only the first N selected photos.")
        parser.add_argument(
            "--only-missing",
            action="store_true",
            help="Process only photos missing embeddings or captions.",
        )

    def handle(self, *args, **options):
        queryset = Photo.objects.order_by("id")

        photo_id = options.get("photo_id")
        if photo_id:
            queryset = queryset.filter(id=photo_id)

        if options.get("only_missing"):
            queryset = queryset.filter(caption_en="") | queryset.filter(embedding_dimension=0)
            queryset = queryset.order_by("id")

        limit = options.get("limit")
        if limit:
            queryset = queryset[:limit]

        photos = list(queryset)
        if not photos:
            self.stdout.write(self.style.WARNING("No photos selected for reindexing."))
            return

        self.stdout.write(f"Reindexing {len(photos)} photos...")
        processed_count = 0

        for photo in photos:
            image_path = Path(photo.image.path)
            if not image_path.exists():
                raise CommandError(f"Photo file not found: {image_path}")

            with image_path.open("rb") as image_file:
                index_data = create_photo_index(image_file)

            embedding_data = index_data["embedding"]
            photo.embedding_model = str(embedding_data["model_name"])
            photo.embedding_pretrained_tag = str(embedding_data["pretrained_tag"])
            photo.embedding_dimension = int(embedding_data["dimension"])
            photo.embedding_vector = list(embedding_data["vector"])
            photo.embedding_created_at = timezone.now()
            photo.caption_model = str(index_data["caption_model_name"])
            photo.caption_en = str(index_data["caption_en"])
            photo.caption_tokens = list(index_data["caption_tokens"])
            photo.caption_created_at = timezone.now()
            photo.processing_status = "indexed"
            photo.save(
                update_fields=[
                    "embedding_model",
                    "embedding_pretrained_tag",
                    "embedding_dimension",
                    "embedding_vector",
                    "embedding_created_at",
                    "caption_model",
                    "caption_en",
                    "caption_tokens",
                    "caption_created_at",
                    "processing_status",
                    "updated_at",
                ]
            )
            processed_count += 1
            self.stdout.write(f"[{processed_count}/{len(photos)}] indexed photo #{photo.id} {photo.original_filename}")

        self.stdout.write(self.style.SUCCESS(f"Finished reindexing {processed_count} photos."))
