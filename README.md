# Liquid Photos

Liquid Photos — это demo-ориентированная умная фотобиблиотека для университетской лабораторной работы по нейросетям, семантическому поиску по медиа и поиску людей на фотографиях.

Сейчас проект разделён на три явные части:

- `Backend/` — Django-приложение, API, авторизация, загрузка фото, локальное хранение, группировка людей
- `WebUI/` — интерфейс на React 19 + TypeScript + Vite
- `CoreAI/` — изолированный AI-модуль для эмбеддингов, подписей, query rewrite и извлечения лиц

## Текущее состояние

Этот репозиторий больше не является frontend-only прототипом. В нём уже есть рабочее локальное веб-приложение со следующими возможностями:

- Django backend с сессионной авторизацией
- загрузка фотографий и личная медиатека
- API семантического поиска по фото
- API группировки и просмотра людей
- переименование найденных людей
- React-интерфейс, подключённый к backend endpoint-ам
- локальная SQLite-база и локальное хранение медиа
- отдельная инициализация AI-модуля через `CoreAI.config`

Проект по-прежнему ориентирован на учебный demo-сценарий:

- небольшой локальный датасет
- малое число пользователей
- local-first хранение
- понятная архитектура важнее production-сложности

## Возможности

### Медиатека

- личная библиотека фотографий пользователя
- квадратная сетка изображений
- локальная загрузка фото
- удаление фотографий

### Интеллектуальный поиск

- поиск по фото на естественном языке
- AI-нормализация и переписывание запроса
- текстовые эмбеддинги для поиска
- гибридное ранжирование по embedding similarity и caption token match

### Люди

- извлечение лиц из загруженных фотографий
- кластеризация одного и того же человека между разными фото
- список людей с preview-портретами
- переименование человека
- просмотр фото, относящихся к выбранному человеку

## Стек технологий

### Backend

- Python
- Django 5.2
- SQLite
- Pillow
- scikit-learn

### Web UI

- React 19
- TypeScript
- Vite
- обычный CSS

### AI-модуль

- OpenCLIP
- PyTorch
- Transformers
- InsightFace
- ONNX Runtime

## Структура репозитория

```text
.
├── Backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── run_app.py
│   ├── liquid_photos/
│   └── web/
├── CoreAI/
│   ├── nova_ai_shipping/
│   └── models/
├── WebUI/
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── vite.config.ts
│   ├── public/demo/
│   └── src/
├── CoreAI.config
├── Local_DB/
├── templates/
└── AGENTS.md
```

## Локальная разработка

### Frontend

Установка зависимостей:

```bash
cd WebUI && pnpm install
```

Запуск Vite dev server:

```bash
cd WebUI && pnpm dev
```

Запуск Vite в локальной сети:

```bash
cd WebUI && pnpm dev --host 0.0.0.0
```

Production-сборка frontend:

```bash
cd WebUI && pnpm build
```

### Backend

Установка Python-зависимостей в ваше окружение:

```bash
pip install -r Backend/requirements.txt
```

Проверка Django:

```bash
.venv/bin/python Backend/manage.py check
```

Применение миграций:

```bash
.venv/bin/python Backend/manage.py migrate
```

Запуск интегрированного сценария приложения:

```bash
python Backend/run_app.py
```

Эта команда:

- проверяет наличие зависимостей `WebUI`
- собирает frontend bundle
- применяет миграции
- запускает `collectstatic`
- стартует Django на `http://127.0.0.1:8000/`

При необходимости Django можно запускать напрямую:

```bash
.venv/bin/python Backend/manage.py runserver 127.0.0.1:8000
```

## Конфигурация

### Локальные данные

По умолчанию приложение хранит SQLite-базу и загруженные файлы в `Local_DB/`.

```env
LIQUID_PHOTOS_DATA_DIR=./Local_DB
DJANGO_ALLOWED_HOSTS=*
DJANGO_DEBUG=true
```

Типичная структура:

```text
Local_DB/
├── db.sqlite3
└── media/
    └── users/
        └── <username>/
            ├── <uuid>.jpg
            └── faces/
```

### AI runtime

Поведение AI-модуля настраивается через `CoreAI.config`.

Важные параметры:

- `bEnableAiModule`
- `bEnableFaceModule`
- `sComputeDevice`
- `sQueryRewriteModelPath`

Django импортирует AI-модуль из `CoreAI/`, но сам runtime-код живёт внутри Python-пакета `nova_ai_shipping`.

## Основные backend endpoint-ы

- `GET /api/ai/status`
- `GET /api/auth/me`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `POST /api/auth/register`
- `GET /api/photos`
- `POST /api/photos/upload`
- `POST /api/photos/search`
- `POST /api/photos/<id>/delete`
- `GET /api/people`
- `GET /api/people/<id>/photos`
- `POST /api/people/<id>/rename`

## Примечания

- пользовательский интерфейс должен оставаться русскоязычным по умолчанию
- регистрация сейчас закрыта в backend-логике
- `README.md` следует воспринимать как актуальное описание архитектуры, а не как историческую заметку о прототипе
