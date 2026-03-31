from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np
from django.core.files.base import ContentFile
from django.db.models import Count, Prefetch
from django.utils import timezone
from sklearn.cluster import AgglomerativeClustering
from sklearn.decomposition import PCA

from CoreAI.faces import extract_faces, get_face_runtime_config
from web.models import DetectedFace, Person, Photo


def _dot_similarity(left: list[float], right: list[float]) -> float:
    return sum(float(left_item) * float(right_item) for left_item, right_item in zip(left, right, strict=True))


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
            "file_extension",
            "file_size_bytes",
            "mime_type",
            "processing_status",
            "embedding_model",
            "embedding_pretrained_tag",
            "embedding_dimension",
            "embedding_vector",
            "embedding_created_at",
            "caption_model",
            "caption_en",
            "caption_ru",
            "caption_ru_synonyms",
            "search_terms_ru",
            "search_terms_en",
            "search_synonyms_ru",
            "entity_payload",
            "caption_created_at",
            "created_at",
        )
    )
    return [
        {
            "id": photo.id,
            "url": photo.image.url,
            "originalFilename": photo.original_filename,
            "fileExtension": photo.file_extension,
            "fileSizeBytes": photo.file_size_bytes,
            "mimeType": photo.mime_type,
            "processingStatus": photo.processing_status,
            "hasEmbedding": bool(photo.embedding_dimension and photo.embedding_vector),
            "embeddingDimension": photo.embedding_dimension,
            "embeddingModel": photo.embedding_model,
            "embeddingPretrainedTag": photo.embedding_pretrained_tag,
            "embeddingCreatedAt": photo.embedding_created_at.isoformat() if photo.embedding_created_at else "",
            "captionModel": photo.caption_model,
            "captionEn": photo.caption_en,
            "captionRu": photo.caption_ru,
            "captionRuSynonyms": list(photo.caption_ru_synonyms),
            "searchTermsRu": list(photo.search_terms_ru),
            "searchTermsEn": list(photo.search_terms_en),
            "searchSynonymsRu": list(photo.search_synonyms_ru),
            "entityPayload": dict(photo.entity_payload),
            "captionCreatedAt": photo.caption_created_at.isoformat() if photo.caption_created_at else "",
            "createdAt": photo.created_at.isoformat(),
        }
        for photo in photos
    ]


def _project_face_embeddings(vectors: list[list[float]]) -> list[tuple[float, float]]:
    if not vectors:
        return []

    matrix = np.asarray(vectors, dtype=np.float32)
    if len(vectors) == 1:
        return [(0.5, 0.5)]

    if matrix.shape[1] >= 2:
        projector = PCA(n_components=2)
        reduced = projector.fit_transform(matrix)
    else:
        reduced = np.column_stack([matrix[:, 0], np.zeros(len(vectors), dtype=np.float32)])

    xs = reduced[:, 0]
    ys = reduced[:, 1]
    min_x, max_x = float(xs.min()), float(xs.max())
    min_y, max_y = float(ys.min()), float(ys.max())
    range_x = max(max_x - min_x, 1e-6)
    range_y = max(max_y - min_y, 1e-6)

    projected: list[tuple[float, float]] = []
    for x_value, y_value in zip(xs, ys, strict=True):
        normalized_x = 0.12 + (float(x_value) - min_x) / range_x * 0.76
        normalized_y = 0.12 + (float(y_value) - min_y) / range_y * 0.76
        projected.append((round(normalized_x, 6), round(normalized_y, 6)))
    return projected


def list_face_map_for_user(user) -> dict[str, object]:
    faces = list(
        DetectedFace.objects.select_related("photo", "person")
        .filter(photo__user=user, embedding_dimension__gt=0)
        .exclude(embedding_vector=[])
        .order_by("person_id", "-quality_score", "id")
    )
    if not faces:
        return {"faces": [], "clusters": [], "clusterEps": float(get_face_runtime_config()["cluster_eps"])}

    vectors = [list(face.embedding_vector) for face in faces]
    projected_points = _project_face_embeddings(vectors)
    cluster_groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    serialized_faces: list[dict[str, object]] = []

    for face, (x_pos, y_pos) in zip(faces, projected_points, strict=True):
        person_id = int(face.person_id) if face.person_id else None
        cluster_id = f"person-{person_id}" if person_id is not None else f"face-{face.id}"
        person_label = ""
        if face.person is not None:
            person_label = face.person.display_name.strip() or f"Человек {face.person_id}"

        payload = {
            "id": face.id,
            "clusterId": cluster_id,
            "personId": person_id,
            "personLabel": person_label,
            "previewUrl": face.preview_image.url if face.preview_image else "",
            "photoId": face.photo_id,
            "photoUrl": face.photo.image.url,
            "photoFilename": face.photo.original_filename,
            "bbox": list(face.bbox),
            "qualityScore": round(float(face.quality_score), 6),
            "detectionScore": round(float(face.detection_score), 6),
            "embeddingDimension": int(face.embedding_dimension),
            "x": x_pos,
            "y": y_pos,
        }
        serialized_faces.append(payload)
        cluster_groups[cluster_id].append(payload)

    clusters: list[dict[str, object]] = []
    for cluster_id, cluster_faces in cluster_groups.items():
        centroid_x = sum(float(face["x"]) for face in cluster_faces) / len(cluster_faces)
        centroid_y = sum(float(face["y"]) for face in cluster_faces) / len(cluster_faces)
        first_face = cluster_faces[0]
        clusters.append(
            {
                "id": cluster_id,
                "personId": first_face["personId"],
                "label": str(first_face["personLabel"] or "Без имени"),
                "faceCount": len(cluster_faces),
                "centroidX": round(centroid_x, 6),
                "centroidY": round(centroid_y, 6),
            }
        )

    return {
        "faces": serialized_faces,
        "clusters": sorted(clusters, key=lambda item: (-int(item["faceCount"]), str(item["id"]))),
        "clusterEps": float(get_face_runtime_config()["cluster_eps"]),
    }


def describe_face_for_user(user, face_id: int) -> dict[str, object] | None:
    faces = list(
        DetectedFace.objects.select_related("photo", "person")
        .filter(photo__user=user, embedding_dimension__gt=0)
        .exclude(embedding_vector=[])
        .order_by("id")
    )
    selected_face = next((face for face in faces if face.id == face_id), None)
    if selected_face is None:
        return None

    selected_vector = list(selected_face.embedding_vector)
    neighbor_payloads: list[dict[str, object]] = []
    for face in faces:
        if face.id == selected_face.id:
            continue
        similarity = _dot_similarity(selected_vector, list(face.embedding_vector))
        same_person = bool(selected_face.person_id and selected_face.person_id == face.person_id)
        neighbor_payloads.append(
            {
                "id": face.id,
                "previewUrl": face.preview_image.url if face.preview_image else "",
                "photoId": face.photo_id,
                "photoFilename": face.photo.original_filename,
                "personId": int(face.person_id) if face.person_id else None,
                "personLabel": (
                    face.person.display_name.strip() or f"Человек {face.person_id}"
                    if face.person_id and face.person is not None
                    else ""
                ),
                "similarity": round(float(similarity), 6),
                "distance": round(float(1.0 - similarity), 6),
                "sameCluster": same_person,
            }
        )

    neighbor_payloads.sort(key=lambda item: (not bool(item["sameCluster"]), -float(item["similarity"])))
    person_faces = [face for face in faces if selected_face.person_id and face.person_id == selected_face.person_id]
    centroid_similarity = 0.0
    if person_faces:
        centroid_vector = np.mean(np.asarray([list(face.embedding_vector) for face in person_faces], dtype=np.float32), axis=0)
        centroid_norm = float(np.linalg.norm(centroid_vector))
        if centroid_norm > 0:
            centroid_vector = centroid_vector / centroid_norm
            centroid_similarity = _dot_similarity(selected_vector, centroid_vector.astype(np.float32).tolist())

    return {
        "face": {
            "id": selected_face.id,
            "previewUrl": selected_face.preview_image.url if selected_face.preview_image else "",
            "photoId": selected_face.photo_id,
            "photoUrl": selected_face.photo.image.url,
            "photoFilename": selected_face.photo.original_filename,
            "personId": int(selected_face.person_id) if selected_face.person_id else None,
            "personLabel": (
                selected_face.person.display_name.strip() or f"Человек {selected_face.person_id}"
                if selected_face.person_id and selected_face.person is not None
                else ""
            ),
            "bbox": list(selected_face.bbox),
            "qualityScore": round(float(selected_face.quality_score), 6),
            "detectionScore": round(float(selected_face.detection_score), 6),
            "clusterFaceCount": len(person_faces) if person_faces else 1,
            "centroidSimilarity": round(float(centroid_similarity), 6),
        },
        "neighbors": neighbor_payloads[:8],
        "clusterEps": float(get_face_runtime_config()["cluster_eps"]),
    }
