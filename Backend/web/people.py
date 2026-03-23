from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np
from django.core.files.base import ContentFile
from django.db.models import Count, Prefetch
from django.utils import timezone
from sklearn.cluster import AgglomerativeClustering

from CoreAI.faces import extract_faces, get_face_runtime_config
from web.models import DetectedFace, Person, Photo


def _delete_face_preview(face: DetectedFace) -> None:
    if face.preview_image:
        face.preview_image.delete(save=False)


def clear_photo_faces(photo: Photo) -> None:
    for face in photo.detected_faces.all():
        _delete_face_preview(face)
    photo.detected_faces.all().delete()


def index_photo_faces(photo: Photo, file_obj) -> list[DetectedFace]:
    clear_photo_faces(photo)
    file_obj.seek(0)
    face_payloads = extract_faces(file_obj)
    created_faces: list[DetectedFace] = []

    for index, payload in enumerate(face_payloads, start=1):
        face = DetectedFace(
            photo=photo,
            bbox=list(payload["bbox"]),
            landmarks=list(payload["landmarks"]),
            detection_score=float(payload["detection_score"]),
            quality_score=float(payload["quality_score"]),
            embedding_model=str(payload["embedding_model"]),
            embedding_dimension=int(payload["embedding_dimension"]),
            embedding_vector=list(payload["embedding_vector"]),
            embedding_created_at=timezone.now(),
        )
        face.preview_image.save(
            f"{Path(photo.original_filename).stem}-face-{index}.jpg",
            ContentFile(bytes(payload["preview_bytes"])),
            save=False,
        )
        face.save()
        created_faces.append(face)

    return created_faces


def reindex_photo_faces_from_storage(photo: Photo) -> list[DetectedFace]:
    image_path = Path(photo.image.path)
    with image_path.open("rb") as image_file:
        return index_photo_faces(photo, image_file)


def _cluster_labels(vectors: list[list[float]], eps: float) -> np.ndarray:
    if not vectors:
        return np.array([], dtype=np.int32)

    if len(vectors) == 1:
        return np.array([0], dtype=np.int32)

    matrix = np.asarray(vectors, dtype=np.float32)
    # Complete-linkage is stricter than DBSCAN chaining and works better here
    # for small personal libraries where one face should not bridge two groups.
    clustering = AgglomerativeClustering(
        n_clusters=None,
        metric="cosine",
        linkage="complete",
        distance_threshold=eps,
    )
    return clustering.fit_predict(matrix)


def cluster_user_faces(user) -> list[Person]:
    config = get_face_runtime_config()
    faces = list(
        DetectedFace.objects.select_related("photo", "person")
        .filter(photo__user=user, embedding_dimension__gt=0)
        .order_by("id")
    )
    existing_people = {person.id: person for person in Person.objects.filter(user=user)}

    if not faces:
        for person in existing_people.values():
            person.delete()
        return []

    vectors = [list(face.embedding_vector) for face in faces]
    labels = _cluster_labels(vectors, float(config["cluster_eps"]))
    clusters: dict[int, list[DetectedFace]] = defaultdict(list)
    for face, label in zip(faces, labels, strict=True):
        clusters[int(label)].append(face)

    old_members: dict[int, set[int]] = defaultdict(set)
    for face in faces:
        if face.person_id:
            old_members[int(face.person_id)].add(face.id)

    reused_people: set[int] = set()
    assigned_people: list[Person] = []

    for label in sorted(clusters):
        cluster_faces = clusters[label]
        cluster_face_ids = {face.id for face in cluster_faces}

        best_person_id = None
        best_overlap = 0
        for person_id, member_ids in old_members.items():
            if person_id in reused_people:
                continue
            overlap = len(cluster_face_ids & member_ids)
            if overlap > best_overlap:
                best_overlap = overlap
                best_person_id = person_id

        if best_person_id is not None and best_overlap > 0:
            person = existing_people[best_person_id]
            reused_people.add(best_person_id)
        else:
            person = Person.objects.create(user=user)

        assigned_people.append(person)
        cluster_faces.sort(key=lambda face: (-face.quality_score, face.id))
        for face in cluster_faces:
            if face.person_id != person.id:
                face.person = person
                face.save(update_fields=["person", "updated_at"])

    assigned_ids = {person.id for person in assigned_people}
    for face in faces:
        if face.person_id and face.person_id not in assigned_ids:
            face.person = None
            face.save(update_fields=["person", "updated_at"])

    for person_id, person in existing_people.items():
        if person_id not in assigned_ids:
            person.delete()

    return list(Person.objects.filter(id__in=assigned_ids).order_by("id"))


def serialize_person(person: Person, *, fallback_index: int) -> dict[str, object]:
    preview_face = next(iter(getattr(person, "prefetched_faces", [])), None)
    face_count = int(getattr(person, "face_count", 0))
    photo_count = int(getattr(person, "photo_count", 0))
    return {
        "id": person.id,
        "displayName": person.display_name,
        "fallbackName": f"Человек {fallback_index}",
        "previewUrl": preview_face.preview_image.url if preview_face and preview_face.preview_image else "",
        "faceCount": face_count,
        "photoCount": photo_count,
    }


def list_people_for_user(user) -> list[dict[str, object]]:
    people = list(
        Person.objects.filter(user=user)
        .annotate(face_count=Count("faces"), photo_count=Count("faces__photo", distinct=True))
        .prefetch_related(
            Prefetch(
                "faces",
                queryset=DetectedFace.objects.only("id", "person_id", "preview_image", "quality_score").order_by(
                    "-quality_score", "id"
                ),
                to_attr="prefetched_faces",
            )
        )
        .order_by("-photo_count", "-face_count", "id")
    )
    return [serialize_person(person, fallback_index=index) for index, person in enumerate(people, start=1)]


def list_person_photos(person: Person) -> list[dict[str, object]]:
    photos = list(
        Photo.objects.filter(user=person.user, detected_faces__person=person)
        .distinct()
        .order_by("-created_at")
        .only(
            "id",
            "image",
            "original_filename",
            "processing_status",
            "created_at",
        )
    )
    return [
        {
            "id": photo.id,
            "url": photo.image.url,
            "originalFilename": photo.original_filename,
            "processingStatus": photo.processing_status,
        }
        for photo in photos
    ]
