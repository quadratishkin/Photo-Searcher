from __future__ import annotations

import asyncio
import html
import logging
import os
from threading import Event, Lock, Thread
from pathlib import Path

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, ReplyKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from liquid_photos.env import load_project_env
from web.people import describe_face_for_user, list_face_map_for_user
from web.services import (
    delete_photo_for_user,
    get_telegram_user,
    get_person_photos_payload_for_user,
    list_people_payload_for_user,
    login_telegram_user,
    list_photos_for_user,
    logout_telegram_user,
    rename_person_for_user,
    search_photos_for_user,
    upload_photo_files_for_user,
)


logger = logging.getLogger(__name__)
LIBRARY_PAGE_SIZE = 6
PEOPLE_PAGE_SIZE = 8
FACES_PAGE_SIZE = 8
_background_thread: Thread | None = None
_background_lock = Lock()
_background_started = False
_background_stop_event = Event()
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [["Библиотека", "Поиск"], ["Загрузка", "Лица"], ["Анализ лиц", "Помощь"], ["Выйти"]],
    resize_keyboard=True,
)
LOGGED_OUT_KEYBOARD = ReplyKeyboardMarkup([["Старт", "Войти"], ["Помощь"]], resize_keyboard=True)


def build_application(token: str) -> Application:
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("library", library_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("people", people_command))
    application.add_handler(CommandHandler("faces", people_command))
    application.add_handler(CommandHandler("facemap", facemap_command))
    application.add_handler(CommandHandler("face", face_command))
    application.add_handler(CommandHandler("login", login_command))
    application.add_handler(CommandHandler("rename", rename_command))
    application.add_handler(CommandHandler("delete", delete_command))
    application.add_handler(CommandHandler("logout", logout_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo_upload))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    return application


def get_bot_token() -> str:
    load_project_env()
    token = os.environ.get("LIQUID_PHOTOS_TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Не задан LIQUID_PHOTOS_TELEGRAM_BOT_TOKEN.")
    return token


async def _run_polling_until_stopped(stop_event: Event) -> None:
    application = build_application(get_bot_token())
    await application.initialize()
    await application.start()

    if application.updater is None:
        raise RuntimeError("Telegram updater не инициализирован.")

    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Telegram bot polling started in shared process")
    try:
        while not stop_event.is_set():
            await asyncio.sleep(0.5)
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("Telegram bot polling stopped")


def _background_runner() -> None:
    try:
        asyncio.run(_run_polling_until_stopped(_background_stop_event))
    except Exception:
        logger.exception("Telegram bot background runner failed")


def start_polling_background() -> bool:
    global _background_started, _background_thread

    with _background_lock:
        if _background_started:
            return False

        _background_stop_event.clear()
        _background_thread = Thread(
            target=_background_runner,
            name="liquid-photos-telegram-bot",
            daemon=True,
        )
        _background_thread.start()
        _background_started = True
        return True


async def get_existing_user_from_update(update: Update):
    telegram_user = update.effective_user
    if telegram_user is None:
        raise RuntimeError("Telegram update не содержит пользователя.")
    return await sync_to_async(get_telegram_user)(telegram_user.id)


async def ensure_logged_in_user(update: Update):
    user = await get_existing_user_from_update(update)
    if user is not None:
        return user
    await update.effective_message.reply_text(
        "Сессия Telegram завершена. Нажмите «Старт» или отправьте /start, чтобы войти снова.",
        reply_markup=LOGGED_OUT_KEYBOARD,
    )
    return None


def build_library_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup | None:
    buttons: list[InlineKeyboardButton] = []
    if page > 0:
        buttons.append(InlineKeyboardButton("← Назад", callback_data=f"library:{page - 1}"))
    if page + 1 < total_pages:
        buttons.append(InlineKeyboardButton("Дальше →", callback_data=f"library:{page + 1}"))
    if not buttons:
        return None
    return InlineKeyboardMarkup([buttons])


def build_people_keyboard(people: list[dict], page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                person["displayName"] or person["fallbackName"],
                callback_data=f"person:{person['id']}",
            )
        ]
        for person in people
    ]
    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("← Назад", callback_data=f"people:{page - 1}"))
    if page + 1 < total_pages:
        nav_row.append(InlineKeyboardButton("Дальше →", callback_data=f"people:{page + 1}"))
    if nav_row:
        rows.append(nav_row)
    return InlineKeyboardMarkup(rows)


def build_faces_keyboard(faces: list[dict], page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                build_face_button_label(face),
                callback_data=f"face:{face['id']}",
            )
        ]
        for face in faces
    ]
    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("← Назад", callback_data=f"faces:{page - 1}"))
    if page + 1 < total_pages:
        nav_row.append(InlineKeyboardButton("Дальше →", callback_data=f"faces:{page + 1}"))
    if nav_row:
        rows.append(nav_row)
    return InlineKeyboardMarkup(rows)


def slice_page(items: list[dict], page: int, page_size: int) -> tuple[list[dict], int, int]:
    total_pages = max(1, (len(items) + page_size - 1) // page_size)
    safe_page = max(0, min(page, total_pages - 1))
    start = safe_page * page_size
    end = start + page_size
    return items[start:end], safe_page, total_pages


def escape(value: str) -> str:
    return html.escape(value, quote=False)


def clip_text(value: str, limit: int) -> str:
    normalized = " ".join(str(value).split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 1)].rstrip() + "…"


def build_face_button_label(face: dict) -> str:
    label = str(face.get("personLabel") or f"Лицо #{face['id']}")
    filename = clip_text(str(face.get("photoFilename") or ""), 18)
    return clip_text(f"{label} | {filename}", 60)


def build_photo_caption(photo: dict, prefix: str = "") -> str:
    title = escape(photo["originalFilename"])
    caption_ru = escape(str(photo.get("captionRu", "")).strip())
    photo_id = int(photo["id"])
    lines = [prefix + f"<b>{title}</b>"]
    lines.append(f"ID: <code>{photo_id}</code>")
    if caption_ru:
        lines.append(caption_ru[:900])
    lines.append(
        f"Статус: {escape(str(photo.get('processingStatus', '')))} | "
        f"Размер: {escape(str(photo.get('fileSizeBytes', '')))} B"
    )
    return "\n".join(lines)


async def send_photo_batch(message, photos: list[dict], *, header: str, reply_markup=None) -> None:
    if not photos:
        await message.reply_text(header, reply_markup=reply_markup)
        return

    media_group = []
    file_handles = []
    try:
        for index, photo in enumerate(photos):
            image_path = Path(settings.MEDIA_ROOT) / Path(photo["url"]).relative_to("/media")
            file_handle = image_path.open("rb")
            file_handles.append(file_handle)
            caption = build_photo_caption(photo, prefix=f"{index + 1}. ")
            if index == 0:
                caption = f"{escape(header)}\n\n{caption}"
            media_group.append(
                InputMediaPhoto(
                    media=file_handle,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                )
            )
        await message.reply_media_group(media=media_group)
    finally:
        for file_handle in file_handles:
            file_handle.close()

    if reply_markup is not None:
        await message.reply_text("Навигация:", reply_markup=reply_markup)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    user = await get_existing_user_from_update(update)
    if user is None:
        await update.effective_message.reply_text(
            (
                "Liquid Photos для Telegram готов.\n\n"
                "Сначала войдите в существующий аккаунт приложения.\n"
                "Команда: /login <username> <password>\n"
                "Или нажмите кнопку «Войти» для пошагового входа."
            ),
            reply_markup=LOGGED_OUT_KEYBOARD,
        )
        return

    name = update.effective_user.first_name or user.username
    await update.effective_message.reply_text(
        (
            f"Liquid Photos для Telegram готов.\n"
            f"Пользователь: {name}\n"
            f"Аккаунт приложения: {user.username}\n\n"
            "Доступно:\n"
            "/library или кнопка «Библиотека»\n"
            "/search <запрос> или кнопка «Поиск»\n"
            "отправка фото для загрузки\n"
            "/people или кнопка «Лица»"
        ),
        reply_markup=MAIN_KEYBOARD,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        (
            "Команды:\n"
            "/login <username> <password> войти в аккаунт приложения\n"
            "/logout выйти из Telegram-сессии\n\n"
            "/library показать библиотеку\n"
            "/search <текст> выполнить поиск\n"
            "/people показать найденных людей\n\n"
            "/facemap показать список лиц для анализа\n"
            "/face <id> показать анализ конкретного лица\n"
            "/rename <person_id> <новое имя> переименовать человека\n"
            "/delete <photo_id> удалить фото\n\n"
            "Для загрузки просто отправьте фото или изображение документом."
        ),
        reply_markup=(MAIN_KEYBOARD if await get_existing_user_from_update(update) is not None else LOGGED_OUT_KEYBOARD),
    )


async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if len(args) >= 2:
        username = args[0]
        password = " ".join(args[1:])
        await perform_login(update, context, username, password)
        return

    context.user_data.clear()
    context.user_data["awaiting"] = "login_username"
    await update.effective_message.reply_text(
        "Введите имя пользователя от веб-приложения.",
        reply_markup=LOGGED_OUT_KEYBOARD,
    )


async def perform_login(update: Update, context: ContextTypes.DEFAULT_TYPE, app_username: str, password: str) -> None:
    telegram_user = update.effective_user
    chat = update.effective_chat
    if telegram_user is None or chat is None:
        return

    try:
        user = await sync_to_async(login_telegram_user)(
            telegram_user_id=telegram_user.id,
            chat_id=chat.id,
            username=telegram_user.username or "",
            first_name=telegram_user.first_name or "",
            last_name=telegram_user.last_name or "",
            app_username=app_username,
            password=password,
        )
    except Exception as exc:
        context.user_data["awaiting"] = "login_username"
        context.user_data.pop("login_username", None)
        await update.effective_message.reply_text(str(exc), reply_markup=LOGGED_OUT_KEYBOARD)
        return

    context.user_data.clear()
    await update.effective_message.reply_text(
        f"Вход выполнен. Текущий аккаунт: {user.username}",
        reply_markup=MAIN_KEYBOARD,
    )


async def library_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_logged_in_user(update)
    if user is None:
        return
    await render_library(update.effective_message, user, 0)


async def render_library(message, user, page: int) -> None:
    photos = await sync_to_async(list_photos_for_user)(user)
    if not photos:
        await message.reply_text("Библиотека пока пустая. Отправьте фото в этот чат.", reply_markup=MAIN_KEYBOARD)
        return

    page_items, safe_page, total_pages = slice_page(photos, page, LIBRARY_PAGE_SIZE)
    header = f"Библиотека: страница {safe_page + 1} из {total_pages}. Всего фото: {len(photos)}."
    await send_photo_batch(
        message,
        page_items,
        header=header,
        reply_markup=build_library_keyboard(safe_page, total_pages),
    )
    ids = ", ".join(str(item["id"]) for item in page_items)
    await message.reply_text(
        f"ID фото на этой странице: {ids}\nДля удаления используйте /delete <photo_id>.",
        reply_markup=MAIN_KEYBOARD,
    )


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_logged_in_user(update)
    if user is None:
        return
    query = " ".join(context.args).strip()
    if not query:
        context.user_data["awaiting"] = "search"
        await update.effective_message.reply_text(
            "Отправьте текстовый запрос. Например: красный закат у моря или Анна в парке.",
            reply_markup=MAIN_KEYBOARD,
        )
        return
    await run_search(update.effective_message, user, query)


async def run_search(message, user, query: str) -> None:
    await message.chat.send_action(ChatAction.TYPING)
    try:
        payload = await sync_to_async(search_photos_for_user)(user, query)
    except Exception as exc:
        await message.reply_text(f"Поиск завершился ошибкой: {exc}", reply_markup=MAIN_KEYBOARD)
        return

    photos = payload.get("photos", [])
    matched_person = payload.get("matchedPerson")
    header_parts = [f"Запрос: {query}"]
    if matched_person:
        header_parts.append(f"Фильтр по человеку: {matched_person['displayName']}")
    if payload.get("message"):
        header_parts.append(str(payload["message"]))
    header = "\n".join(header_parts)
    await send_photo_batch(message, photos[: min(6, len(photos))], header=header, reply_markup=None)


async def people_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_logged_in_user(update)
    if user is None:
        return
    await render_people(update.effective_message, user, 0)


async def render_people(message, user, page: int) -> None:
    payload = await sync_to_async(list_people_payload_for_user)(user)
    people = payload["people"]
    if not people:
        await message.reply_text(payload["message"] or "Лица пока не найдены.", reply_markup=MAIN_KEYBOARD)
        return

    page_items, safe_page, total_pages = slice_page(people, page, PEOPLE_PAGE_SIZE)
    lines = [f"Найдено людей: {len(people)}. Выберите человека:"]
    for person in page_items:
        lines.append(
            f"• #{person['id']} {person['displayName'] or person['fallbackName']} | фото: {person['photoCount']} | лиц: {person['faceCount']}"
        )
    lines.append("")
    lines.append("Переименование: /rename <person_id> <новое имя>")
    await message.reply_text(
        "\n".join(lines),
        reply_markup=build_people_keyboard(page_items, safe_page, total_pages),
    )


async def facemap_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_logged_in_user(update)
    if user is None:
        return
    await render_face_map(update.effective_message, user, 0)


async def render_face_map(message, user, page: int) -> None:
    payload = await sync_to_async(list_face_map_for_user)(user)
    faces = payload["faces"]
    clusters = payload["clusters"]
    if not faces:
        await message.reply_text("Подготовленных face embeddings пока нет.", reply_markup=MAIN_KEYBOARD)
        return

    page_items, safe_page, total_pages = slice_page(faces, page, FACES_PAGE_SIZE)
    lines = [
        f"Лиц для анализа: {len(faces)}. Кластеров: {len(clusters)}. Порог: {float(payload['clusterEps']):.2f}",
        "Выберите лицо кнопкой ниже или используйте /face <id>.",
    ]
    for face in page_items:
        lines.append(
            f"• #{face['id']} {face['personLabel'] or 'Без имени'} | {face['photoFilename']} | quality {float(face['qualityScore']):.3f}"
        )
    await message.reply_text(
        "\n".join(lines),
        reply_markup=build_faces_keyboard(page_items, safe_page, total_pages),
    )


async def face_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_logged_in_user(update)
    if user is None:
        return
    if not context.args:
        await update.effective_message.reply_text("Использование: /face <id>", reply_markup=MAIN_KEYBOARD)
        return
    try:
        face_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("ID лица должен быть числом.", reply_markup=MAIN_KEYBOARD)
        return
    await render_face_analysis(update.effective_message, user, face_id)


async def render_face_analysis(message, user, face_id: int) -> None:
    payload = await sync_to_async(describe_face_for_user)(user, face_id)
    if payload is None:
        await message.reply_text("Лицо не найдено.", reply_markup=MAIN_KEYBOARD)
        return

    face = payload["face"]
    lines = [
        f"Лицо #{face['id']}",
        f"Человек: {face['personLabel'] or 'Без имени'}",
        f"Фото: {face['photoFilename']}",
        f"bbox: {', '.join(str(round(value)) for value in face['bbox'])}",
        f"quality: {float(face['qualityScore']):.3f}",
        f"detection: {float(face['detectionScore']):.3f}",
        f"faces in cluster: {int(face['clusterFaceCount'])}",
        f"centroid similarity: {float(face['centroidSimilarity']):.3f}",
        f"cluster eps: {float(payload['clusterEps']):.2f}",
        "",
        "Соседи:",
    ]
    neighbors = payload["neighbors"]
    if neighbors:
        for neighbor in neighbors:
            lines.append(
                f"• #{neighbor['id']} {neighbor['personLabel'] or 'Без имени'} | "
                f"sim {float(neighbor['similarity']):.3f} | dist {float(neighbor['distance']):.3f}"
            )
    else:
        lines.append("• соседей нет")

    photo_path = Path(settings.MEDIA_ROOT) / Path(face["photoUrl"]).relative_to("/media")
    with photo_path.open("rb") as file_handle:
        await message.reply_photo(photo=file_handle, caption="\n".join(lines), reply_markup=MAIN_KEYBOARD)


async def rename_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_logged_in_user(update)
    if user is None:
        return
    if len(context.args) < 2:
        await update.effective_message.reply_text(
            "Использование: /rename <person_id> <новое имя>",
            reply_markup=MAIN_KEYBOARD,
        )
        return
    try:
        person_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("ID человека должен быть числом.", reply_markup=MAIN_KEYBOARD)
        return

    display_name = " ".join(context.args[1:]).strip()
    try:
        payload = await sync_to_async(rename_person_for_user)(user, person_id, display_name)
    except Exception as exc:
        await update.effective_message.reply_text(str(exc), reply_markup=MAIN_KEYBOARD)
        return
    person = payload["person"]
    await update.effective_message.reply_text(
        f"Имя обновлено: #{person['id']} {person['displayName'] or 'Без имени'}",
        reply_markup=MAIN_KEYBOARD,
    )


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_logged_in_user(update)
    if user is None:
        return
    if len(context.args) != 1:
        await update.effective_message.reply_text("Использование: /delete <photo_id>", reply_markup=MAIN_KEYBOARD)
        return
    try:
        photo_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("ID фото должен быть числом.", reply_markup=MAIN_KEYBOARD)
        return

    try:
        payload = await sync_to_async(delete_photo_for_user)(user, photo_id)
    except Exception as exc:
        await update.effective_message.reply_text(str(exc), reply_markup=MAIN_KEYBOARD)
        return
    await update.effective_message.reply_text(payload["message"], reply_markup=MAIN_KEYBOARD)


async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_user = update.effective_user
    if telegram_user is None:
        return

    removed = await sync_to_async(logout_telegram_user)(telegram_user.id)
    context.user_data.clear()
    if not removed:
        await update.effective_message.reply_text(
            "Вы уже вышли. Для нового входа используйте /start.",
            reply_markup=LOGGED_OUT_KEYBOARD,
        )
        return

    await update.effective_message.reply_text(
        "Telegram-сессия завершена. Для нового входа используйте /start.",
        reply_markup=LOGGED_OUT_KEYBOARD,
    )


async def render_person_photos(message, user, person_id: int) -> None:
    try:
        payload = await sync_to_async(get_person_photos_payload_for_user)(user, person_id)
    except Exception as exc:
        await message.reply_text(str(exc), reply_markup=MAIN_KEYBOARD)
        return

    person = payload["person"]
    photos = payload["photos"]
    person_label = person["displayName"] or f"#{person['id']}"
    header = f"Человек: {person_label}\nФото: {len(photos)}"
    await send_photo_batch(message, photos[: min(6, len(photos))], header=header, reply_markup=None)


async def handle_photo_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_logged_in_user(update)
    if user is None:
        return
    message = update.effective_message
    document = message.document if message.document and message.document.mime_type and message.document.mime_type.startswith("image/") else None
    photo = message.photo[-1] if message.photo else None
    if document is None and photo is None:
        await message.reply_text("Отправьте изображение как фото или документ.", reply_markup=MAIN_KEYBOARD)
        return

    await message.chat.send_action(ChatAction.UPLOAD_PHOTO)
    telegram_file = await (document or photo).get_file()
    file_bytes = await telegram_file.download_as_bytearray()
    original_name = (
        document.file_name
        if document is not None and document.file_name
        else f"telegram_{(document or photo).file_unique_id}.jpg"
    )
    uploaded_file = SimpleUploadedFile(
        name=original_name,
        content=bytes(file_bytes),
        content_type=(document.mime_type if document is not None else "image/jpeg"),
    )

    try:
        payload = await sync_to_async(upload_photo_files_for_user)(user, [uploaded_file])
    except Exception as exc:
        await message.reply_text(f"Загрузка не удалась: {exc}", reply_markup=MAIN_KEYBOARD)
        return

    context.user_data.pop("awaiting", None)
    await message.reply_text(payload["message"], reply_markup=MAIN_KEYBOARD)
    await render_library(message, user, 0)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    text = (message.text or "").strip()
    normalized = text.casefold()

    if normalized in {"старт", "start"}:
        await start_command(update, context)
        return
    if normalized == "войти":
        await login_command(update, context)
        return
    if normalized == "помощь":
        await help_command(update, context)
        return
    if normalized == "выйти":
        await logout_command(update, context)
        return

    awaiting = context.user_data.get("awaiting")
    if awaiting == "login_username":
        context.user_data["awaiting"] = "login_password"
        context.user_data["login_username"] = text
        await message.reply_text("Введите пароль.", reply_markup=LOGGED_OUT_KEYBOARD)
        return
    if awaiting == "login_password":
        username = str(context.user_data.get("login_username", "")).strip()
        await perform_login(update, context, username, text)
        return

    user = await ensure_logged_in_user(update)
    if user is None:
        return

    if normalized == "библиотека":
        await render_library(message, user, 0)
        return
    if normalized == "поиск":
        context.user_data["awaiting"] = "search"
        await message.reply_text("Отправьте текстовый запрос для поиска.", reply_markup=MAIN_KEYBOARD)
        return
    if normalized in {"лица", "люди"}:
        await render_people(message, user, 0)
        return
    if normalized == "анализ лиц":
        await render_face_map(message, user, 0)
        return
    if normalized == "загрузка":
        await message.reply_text("Отправьте одно или несколько фото в этот чат.", reply_markup=MAIN_KEYBOARD)
        return

    if awaiting == "search":
        context.user_data.pop("awaiting", None)
        await run_search(message, user, text)
        return

    await message.reply_text(
        "Не понял сообщение. Используйте кнопки ниже или отправьте /help.",
        reply_markup=MAIN_KEYBOARD,
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = await ensure_logged_in_user(update)
    if user is None:
        return
    data = query.data or ""
    if data.startswith("library:"):
        page = int(data.split(":", 1)[1])
        await render_library(query.message, user, page)
        return
    if data.startswith("people:"):
        page = int(data.split(":", 1)[1])
        await render_people(query.message, user, page)
        return
    if data.startswith("faces:"):
        page = int(data.split(":", 1)[1])
        await render_face_map(query.message, user, page)
        return
    if data.startswith("person:"):
        person_id = int(data.split(":", 1)[1])
        await render_person_photos(query.message, user, person_id)
        return
    if data.startswith("face:"):
        face_id = int(data.split(":", 1)[1])
        await render_face_analysis(query.message, user, face_id)
        return


def run_polling() -> None:
    token = get_bot_token()
    application = build_application(token)
    logger.info("Starting Telegram bot polling")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
