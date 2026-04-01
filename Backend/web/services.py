from __future__ import annotations

import logging
import math
import re
from pathlib import Path

from django.contrib.auth import authenticate, get_user_model
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils.crypto import get_random_string
from django.utils import timezone

from CoreAI.runtime import (
    analyze_search_query,
    create_photo_index,
    create_text_embedding,
    get_embedding_engine_metadata,
)
from web.models import Person, Photo, TelegramProfile
from web.people import (
    clear_photo_faces,
    cluster_user_faces,
    index_photo_faces,
    list_people_for_user,
    list_person_photos,
)


User = get_user_model()
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
SEARCH_RESULTS_LIMIT = 10
ENTITY_EXACT_WEIGHT = 0.052941
ENTITY_SYNONYM_WEIGHT = 0.021176
ENTITY_GROUP_WEIGHT = 0.023529
ENGLISH_TERM_WEIGHT = 0.002353
EMBEDDING_SCORE_WEIGHT = 0.9
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
QUERY_STOP_WORDS = {
    "a",
    "an",
    "and",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "near",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}
logger = logging.getLogger("liquid_photos.search")
ENTITY_GROUP_NAMES = ("people", "objects", "scene", "actions", "attributes")


def serialize_photo(photo: Photo) -> dict:
    return {
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


def serialize_search_hit(photo: Photo, score: float) -> dict:
    normalized_score = max(0.0, min(1.0, score))
    payload = serialize_photo(photo)
    payload.update(
        {
            "score": round(score, 6),
            "scorePercent": round(normalized_score * 100, 2),
        }
    )
    return payload


def is_valid_embedding_vector(vector: object, dimension: int) -> bool:
    if not isinstance(vector, list) or len(vector) != dimension:
        return False
    return all(isinstance(value, (int, float)) and math.isfinite(float(value)) for value in vector)


def dot_product(left: list[float], right: list[float]) -> float:
    return sum(float(left_item) * float(right_item) for left_item, right_item in zip(left, right, strict=True))


def extract_query_tokens(text: str) -> list[str]:
    tokens = TOKEN_PATTERN.findall(text.strip().lower())
    unique_tokens: list[str] = []
    seen_tokens: set[str] = set()
    for token in tokens:
        if len(token) <= 1 or token in QUERY_STOP_WORDS or token in seen_tokens:
            continue
        seen_tokens.add(token)
        unique_tokens.append(token)
    return unique_tokens


def score_caption_match(query_tokens: list[str], caption_tokens: object) -> tuple[float, float]:
    if not query_tokens or not isinstance(caption_tokens, list):
        return 0.0, 0.0

    normalized_caption_tokens = {
        str(token).strip().lower()
        for token in caption_tokens
        if isinstance(token, str) and str(token).strip()
    }
    if not normalized_caption_tokens:
        return 0.0, 0.0

    matched_tokens = [token for token in query_tokens if token in normalized_caption_tokens]
    if not matched_tokens:
        return 0.0, 0.0

    match_ratio = len(matched_tokens) / len(query_tokens)
    token_bonus = min(1.0, len(matched_tokens) / max(3, len(normalized_caption_tokens)))
    return match_ratio, token_bonus


def normalize_search_term(value: str) -> str:
    normalized = re.sub(r"\s+", " ", str(value).strip()).casefold()
    return normalized


def prepare_term_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []

    terms: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        normalized = normalize_search_term(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        terms.append(normalized)
    return terms


def prepare_entity_payload(value: object) -> dict[str, list[str]]:
    source = value if isinstance(value, dict) else {}
    return {
        group_name: prepare_term_list(source.get(group_name, []))
        for group_name in ENTITY_GROUP_NAMES
    }


def score_term_overlap(query_terms: list[str], candidate_terms: set[str]) -> tuple[float, list[str]]:
    if not query_terms:
        return 0.0, []

    matched = [term for term in query_terms if term in candidate_terms]
    if not matched:
        return 0.0, []
    return len(matched) / len(query_terms), matched


def score_group_overlap(query_entities: dict[str, list[str]], photo_entities: dict[str, list[str]]) -> tuple[float, dict[str, list[str]]]:
    group_scores: list[float] = []
    matched_groups: dict[str, list[str]] = {}

    for group_name in ENTITY_GROUP_NAMES:
        query_terms = query_entities.get(group_name, [])
        if not query_terms:
            continue

        photo_terms = set(photo_entities.get(group_name, []))
        if not photo_terms:
            group_scores.append(0.0)
            continue

        matched = [term for term in query_terms if term in photo_terms]
        group_scores.append(len(matched) / len(query_terms))
        if matched:
            matched_groups[group_name] = matched

    if not group_scores:
        return 0.0, {}
    return sum(group_scores) / len(group_scores), matched_groups


def normalize_person_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def find_person_match(user, query: str) -> tuple[Person | None, str]:
    normalized_query = normalize_person_name(query)
    if not normalized_query:
        return None, query.strip()

    best_match: Person | None = None
    best_span: tuple[int, int] | None = None
    best_name_length = -1

    for person in Person.objects.filter(user=user).exclude(display_name="").only("id", "display_name"):
        display_name = str(person.display_name).strip()
        normalized_name = normalize_person_name(display_name)
        if not normalized_name:
            continue

        pattern = re.compile(rf"(?<!\w){re.escape(normalized_name)}(?!\w)")
        match = pattern.search(normalized_query)
        if match is None:
            continue

        if len(normalized_name) > best_name_length:
            best_match = person
            best_span = match.span()
            best_name_length = len(normalized_name)

    if best_match is None or best_span is None:
        return None, query.strip()

    query_without_name = normalize_person_name(
        f"{normalized_query[: best_span[0]]} {normalized_query[best_span[1] :]}"
    )
    return best_match, query_without_name


def list_photos_for_user(user) -> list[dict]:
    return [serialize_photo(photo) for photo in Photo.objects.filter(user=user)]


def list_people_payload_for_user(user) -> dict:
    people = list_people_for_user(user)
    message = ""
    if not people:
        if Photo.objects.filter(user=user).exists():
            message = "Лица ещё не сгруппированы. Загрузите фото с лицами или выполните переиндексацию людей."
        else:
            message = "Загрузите фотографии, чтобы система могла найти и сгруппировать людей."
    return {"people": people, "message": message}


def get_person_photos_payload_for_user(user, person_id: int) -> dict:
    try:
        person = Person.objects.get(id=person_id, user=user)
    except Person.DoesNotExist as exc:
        raise LookupError("Человек не найден.") from exc

    photos = list_person_photos(person)
    return {
        "person": {
            "id": person.id,
            "displayName": person.display_name,
        },
        "photos": photos,
    }


def rename_person_for_user(user, person_id: int, display_name: str) -> dict:
    try:
        person = Person.objects.get(id=person_id, user=user)
    except Person.DoesNotExist as exc:
        raise LookupError("Человек не найден.") from exc

    normalized_name = str(display_name).strip()
    if len(normalized_name) > 120:
        raise ValueError("Имя человека должно быть не длиннее 120 символов.")

    person.display_name = normalized_name
    person.save(update_fields=["display_name", "updated_at"])
    return {
        "person": {
            "id": person.id,
            "displayName": person.display_name,
        }
    }


def search_photos_for_user(user, query: str) -> dict:
    query = str(query).strip()
    if not query:
        raise ValueError("Введите текстовый запрос для поиска.")

    matched_person, semantic_query = find_person_match(user, query)
    logger.info("photo_search.request user=%s query=%r", user.get_username(), query)

    engine_metadata = get_embedding_engine_metadata()
    expected_model_name = str(engine_metadata["model_name"])
    expected_pretrained_tag = str(engine_metadata["pretrained_tag"])
    expected_dimension = int(engine_metadata["embedding_dimension"])
    query_analysis = analyze_search_query(semantic_query or query)
    translated_query = str(query_analysis.get("normalized_en", ""))
    search_prompt_en = str(query_analysis.get("search_prompt_en", translated_query))
    english_query_tokens = prepare_term_list(list(query_analysis.get("keywords_en", [])))
    query_terms_ru = prepare_term_list(list(query_analysis.get("keywords_ru", [])))
    query_synonyms_ru = prepare_term_list(list(query_analysis.get("synonyms_ru", [])))
    query_entities = prepare_entity_payload(query_analysis)

    indexed_photos_queryset = Photo.objects.filter(user=user).exclude(caption_en="")
    if matched_person is not None:
        indexed_photos_queryset = indexed_photos_queryset.filter(detected_faces__person=matched_person).distinct()

    indexed_photos = list(
        indexed_photos_queryset.only(
            "id",
            "image",
            "original_filename",
            "file_extension",
            "mime_type",
            "file_size_bytes",
            "processing_status",
            "created_at",
            "embedding_model",
            "embedding_pretrained_tag",
            "embedding_dimension",
            "embedding_vector",
            "caption_en",
            "caption_ru",
            "caption_ru_synonyms",
            "caption_tokens",
            "search_terms_ru",
            "search_terms_en",
            "search_synonyms_ru",
            "entity_payload",
            "caption_model",
            "caption_created_at",
        )
    )
    if not indexed_photos:
        person_message = ""
        if matched_person is not None:
            person_message = f" Для человека «{matched_person.display_name}» пока нет проиндексированных фото."
        return {
            "query": query,
            "semanticQuery": semantic_query,
            "photos": [],
            "totalIndexedPhotos": 0,
            "matchedPerson": (
                {
                    "id": matched_person.id,
                    "displayName": matched_person.display_name,
                }
                if matched_person is not None
                else None
            ),
            "message": f"В вашей медиатеке пока нет проиндексированных фото для поиска по сущностям и текстовому индексу.{person_message}",
        }

    query_vector: list[float] | None = None
    if search_prompt_en:
        text_embedding = create_text_embedding(search_prompt_en)
        query_vector = list(text_embedding["vector"])

    search_hits: list[tuple[float, Photo, dict[str, object]]] = []
    skipped_photos = 0

    for photo in indexed_photos:
        photo_terms_ru = set(prepare_term_list(photo.search_terms_ru))
        photo_synonyms_ru = set(prepare_term_list(photo.search_synonyms_ru))
        photo_terms_en = set(prepare_term_list(photo.search_terms_en))
        photo_entities = prepare_entity_payload(photo.entity_payload)

        exact_term_score, matched_terms_ru = score_term_overlap(query_terms_ru, photo_terms_ru)
        synonym_term_score, matched_synonyms_ru = score_term_overlap(
            query_synonyms_ru,
            photo_terms_ru | photo_synonyms_ru,
        )
        group_coverage_score, matched_entity_groups = score_group_overlap(query_entities, photo_entities)

        english_term_score = 0.0
        if english_query_tokens:
            caption_match_ratio, token_bonus = score_caption_match(english_query_tokens, photo.caption_tokens)
            english_term_score = max(
                score_term_overlap(english_query_tokens, photo_terms_en)[0],
                (caption_match_ratio * 0.85) + (token_bonus * 0.15),
            )

        entity_score = (
            (exact_term_score * ENTITY_EXACT_WEIGHT)
            + (synonym_term_score * ENTITY_SYNONYM_WEIGHT)
            + (group_coverage_score * ENTITY_GROUP_WEIGHT)
            + (english_term_score * ENGLISH_TERM_WEIGHT)
        )
        has_compatible_embedding = (
            query_vector is not None
            and photo.embedding_model == expected_model_name
            and photo.embedding_pretrained_tag == expected_pretrained_tag
            and photo.embedding_dimension == expected_dimension
            and is_valid_embedding_vector(photo.embedding_vector, expected_dimension)
        )
        similarity = dot_product(query_vector, photo.embedding_vector) if has_compatible_embedding else 0.0
        embedding_score = max(0.0, min(1.0, (similarity + 1.0) / 2.0)) if has_compatible_embedding else 0.0
        if query_vector is not None and not has_compatible_embedding:
            skipped_photos += 1
        hybrid_score = entity_score + (embedding_score * EMBEDDING_SCORE_WEIGHT)
        debug_meta = {
            "entityScore": round(entity_score, 6),
            "exactTermScore": round(exact_term_score, 6),
            "synonymScore": round(synonym_term_score, 6),
            "groupCoverageScore": round(group_coverage_score, 6),
            "englishTermScore": round(english_term_score, 6),
            "embeddingScore": round(embedding_score, 6),
            "embeddingSimilarity": round(similarity, 6),
            "translatedQuery": translated_query,
            "normalizedRu": str(query_analysis.get("normalized_ru", "")),
            "searchPromptEn": search_prompt_en,
            "queryRewriterUsed": bool(query_analysis.get("used_rewriter", False)),
            "queryRewriteFallbackReason": str(query_analysis.get("fallback_reason", "")),
            "queryAnalysisFallbackReason": str(query_analysis.get("analysisFallbackReason", "")),
            "matchedPersonName": matched_person.display_name if matched_person else "",
            "queryTermsRu": list(query_terms_ru),
            "querySynonymsRu": list(query_synonyms_ru),
            "matchedTermsRu": list(matched_terms_ru),
            "matchedSynonymsRu": list(matched_synonyms_ru),
            "matchedEntityGroups": matched_entity_groups,
        }
        search_hits.append((hybrid_score, photo, debug_meta))

    if not search_hits:
        return {
            "query": query,
            "semanticQuery": semantic_query,
            "photos": [],
            "totalIndexedPhotos": len(indexed_photos),
            "skippedPhotos": skipped_photos,
            "matchedPerson": (
                {
                    "id": matched_person.id,
                    "displayName": matched_person.display_name,
                }
                if matched_person is not None
                else None
            ),
            "message": "Не найдено ни одного фото с валидным embedding-индексом для текущей AI-модели.",
        }

    search_hits.sort(key=lambda item: item[0], reverse=True)
    top_hits = search_hits[:SEARCH_RESULTS_LIMIT]
    return {
        "query": query,
        "semanticQuery": semantic_query,
        "translatedQuery": translated_query,
        "normalizedRu": str(query_analysis.get("normalized_ru", "")),
        "searchPromptEn": search_prompt_en,
        "queryRewriterUsed": bool(query_analysis.get("used_rewriter", False)),
        "queryRewriteFallbackReason": str(query_analysis.get("fallback_reason", "")),
        "queryAnalysisFallbackReason": str(query_analysis.get("analysisFallbackReason", "")),
        "queryTermsRu": list(query_terms_ru),
        "querySynonymsRu": list(query_synonyms_ru),
        "queryEntities": query_entities,
        "matchedPerson": (
            {
                "id": matched_person.id,
                "displayName": matched_person.display_name,
            }
            if matched_person is not None
            else None
        ),
        "photos": [
            {**serialize_search_hit(photo, score), **debug_meta}
            for score, photo, debug_meta in top_hits
        ],
        "topK": SEARCH_RESULTS_LIMIT,
        "totalIndexedPhotos": len(indexed_photos),
        "skippedPhotos": skipped_photos,
        "message": "" if top_hits else "Совпадений не найдено.",
    }


def upload_photo_files_for_user(user, uploaded_files: list[UploadedFile]) -> dict:
    if not uploaded_files:
        raise ValueError("Не выбраны файлы для загрузки.")

    invalid_files = [
        uploaded_file.name
        for uploaded_file in uploaded_files
        if Path(uploaded_file.name).suffix.lower() not in ALLOWED_PHOTO_EXTENSIONS
    ]
    if invalid_files:
        raise ValueError(
            "Можно загружать только изображения поддерживаемых форматов: "
            + ", ".join(sorted(ALLOWED_PHOTO_EXTENSIONS))
        )

    indexed_uploads: list[tuple[UploadedFile, dict]] = []
    for uploaded_file in uploaded_files:
        uploaded_file.seek(0)
        photo_index = create_photo_index(uploaded_file)
        uploaded_file.seek(0)
        indexed_uploads.append((uploaded_file, photo_index))

    created_photos: list[Photo] = []
    face_index_warning = ""
    for uploaded_file, photo_index in indexed_uploads:
        embedding_result = photo_index["embedding"]
        with transaction.atomic():
            photo = Photo(
                user=user,
                original_filename=uploaded_file.name,
                file_extension=Path(uploaded_file.name).suffix.lower(),
                mime_type=getattr(uploaded_file, "content_type", "") or "",
                file_size_bytes=uploaded_file.size,
                processing_status="indexed",
                embedding_model=str(embedding_result["model_name"]),
                embedding_pretrained_tag=str(embedding_result["pretrained_tag"]),
                embedding_dimension=int(embedding_result["dimension"]),
                embedding_vector=list(embedding_result["vector"]),
                embedding_created_at=timezone.now(),
                caption_model=str(photo_index["caption_model_name"]),
                caption_en=str(photo_index["caption_en"]),
                caption_ru=str(photo_index.get("caption_ru", "")),
                caption_ru_synonyms=list(photo_index.get("caption_ru_synonyms", [])),
                caption_tokens=list(photo_index["caption_tokens"]),
                search_terms_ru=list(photo_index.get("search_terms_ru", [])),
                search_terms_en=list(photo_index.get("search_terms_en", [])),
                search_synonyms_ru=list(photo_index.get("search_synonyms_ru", [])),
                entity_payload=dict(photo_index.get("entity_payload", {})),
                caption_created_at=timezone.now(),
            )
            uploaded_file.seek(0)
            photo.image.save(uploaded_file.name, uploaded_file, save=False)
            photo.save()

        created_photos.append(photo)
        try:
            uploaded_file.seek(0)
            index_photo_faces(photo, uploaded_file)
        except Exception as exc:
            if not face_index_warning:
                face_index_warning = f"Группировка лиц временно недоступна: {exc}"

    cluster_error = ""
    try:
        cluster_user_faces(user)
    except Exception as exc:
        cluster_error = f"Не удалось обновить группы людей: {exc}"

    response_message = f"Загружено {len(created_photos)} фото."
    if face_index_warning:
        response_message = f"{response_message} {face_index_warning}"
    elif cluster_error:
        response_message = f"{response_message} {cluster_error}"
    return {
        "message": response_message,
        "photos": [serialize_photo(photo) for photo in created_photos],
    }


def delete_photo_for_user(user, photo_id: int) -> dict:
    try:
        photo = Photo.objects.get(id=photo_id, user=user)
    except Photo.DoesNotExist as exc:
        raise LookupError("Фотография не найдена.") from exc

    clear_photo_faces(photo)
    photo.image.delete(save=False)
    photo.delete()
    try:
        cluster_user_faces(user)
    except Exception:
        pass
    return {"message": "Фотография удалена.", "photoId": photo_id}


def get_or_create_telegram_user(*, telegram_user_id: int, chat_id: int, username: str, first_name: str, last_name: str):
    profile = TelegramProfile.objects.filter(telegram_user_id=telegram_user_id).select_related("user").first()
    if profile is not None:
        updates: list[str] = []
        if profile.telegram_chat_id != chat_id:
            profile.telegram_chat_id = chat_id
            updates.append("telegram_chat_id")
        if profile.telegram_username != username:
            profile.telegram_username = username
            updates.append("telegram_username")
        if profile.telegram_first_name != first_name:
            profile.telegram_first_name = first_name
            updates.append("telegram_first_name")
        if profile.telegram_last_name != last_name:
            profile.telegram_last_name = last_name
            updates.append("telegram_last_name")
        if updates:
            profile.save(update_fields=[*updates, "updated_at"])
        return profile.user

    base_username = f"tg_{telegram_user_id}"
    candidate_username = base_username
    suffix = 1
    while User.objects.filter(username=candidate_username).exists():
        candidate_username = f"{base_username}_{suffix}"
        suffix += 1

    user = User.objects.create_user(
        username=candidate_username,
        password=get_random_string(32),
    )
    TelegramProfile.objects.create(
        user=user,
        telegram_user_id=telegram_user_id,
        telegram_chat_id=chat_id,
        telegram_username=username,
        telegram_first_name=first_name,
        telegram_last_name=last_name,
    )
    return user


def get_telegram_user(telegram_user_id: int):
    profile = TelegramProfile.objects.filter(telegram_user_id=telegram_user_id).select_related("user").first()
    return profile.user if profile is not None else None


def login_telegram_user(
    *,
    telegram_user_id: int,
    chat_id: int,
    username: str,
    first_name: str,
    last_name: str,
    app_username: str,
    password: str,
):
    app_username = str(app_username).strip()
    password = str(password)
    if not app_username or not password:
        raise ValueError("Укажите имя пользователя и пароль.")

    user = authenticate(username=app_username, password=password)
    if user is None:
        raise ValueError("Неверное имя пользователя или пароль.")

    existing_profile = TelegramProfile.objects.filter(telegram_user_id=telegram_user_id).first()
    if existing_profile is not None and existing_profile.user_id != user.id:
        existing_profile.delete()

    TelegramProfile.objects.update_or_create(
        telegram_user_id=telegram_user_id,
        defaults={
            "user": user,
            "telegram_chat_id": chat_id,
            "telegram_username": username,
            "telegram_first_name": first_name,
            "telegram_last_name": last_name,
        },
    )
    return user


def logout_telegram_user(telegram_user_id: int) -> bool:
    profile = TelegramProfile.objects.filter(telegram_user_id=telegram_user_id).select_related("user").first()
    if profile is None:
        return False

    user = profile.user
    profile.delete()

    if (
        user.username.startswith("tg_")
        and not user.is_staff
        and not user.is_superuser
        and not Photo.objects.filter(user=user).exists()
        and not Person.objects.filter(user=user).exists()
    ):
        user.delete()

    return True
