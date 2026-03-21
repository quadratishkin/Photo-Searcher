from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from web.models import Photo
from web.people import cluster_user_faces, reindex_photo_faces_from_storage


class Command(BaseCommand):
    help = "Rebuild detected faces and person clusters for uploaded photos."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--photo-id", type=int, help="Reindex only one photo by id.")
        parser.add_argument("--limit", type=int, help="Process only the first N selected photos.")

    def handle(self, *args, **options):
        queryset = Photo.objects.order_by("id")

        photo_id = options.get("photo_id")
        if photo_id:
            queryset = queryset.filter(id=photo_id)

        limit = options.get("limit")
        if limit:
            queryset = queryset[:limit]

        photos = list(queryset)
        if not photos:
            self.stdout.write(self.style.WARNING("No photos selected for face reindexing."))
            return

        self.stdout.write(f"Reindexing faces for {len(photos)} photos...")
        affected_user_ids: set[int] = set()
        user_model = get_user_model()

        for index, photo in enumerate(photos, start=1):
            reindex_photo_faces_from_storage(photo)
            affected_user_ids.add(int(photo.user_id))
            self.stdout.write(f"[{index}/{len(photos)}] processed photo #{photo.id} {photo.original_filename}")

        for user_id in sorted(affected_user_ids):
            cluster_user_faces(user_model.objects.get(id=user_id))
            self.stdout.write(f"Clustered people for user #{user_id}")

        self.stdout.write(self.style.SUCCESS("Finished rebuilding faces and people."))
