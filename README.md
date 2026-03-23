# Liquid Photos

Liquid Photos is a demo-oriented smart photo library for a university lab project about neural networks, semantic media retrieval, and person discovery in personal photo collections.

The project is now split into three clear parts:

- `Backend/` — Django app, API, auth, uploads, local storage, people grouping
- `WebUI/` — React 19 + TypeScript + Vite interface
- `CoreAI/` — isolated AI runtime for embeddings, captions, query rewrite, and face extraction

## Current State

This repository is no longer a frontend-only prototype. It already contains a working local web application with:

- Django backend with session auth
- photo upload and personal media library
- semantic photo search API
- person discovery / grouping API
- people naming flow
- React UI connected to backend endpoints
- local SQLite database and local media storage
- separate AI module bootstrap through `CoreAI.config`

Current product constraints are still demo-oriented:

- small local dataset
- low user count
- local-first storage
- understandable architecture over production complexity

## Features

### Media Library

- authenticated user photo library
- square media grid UI
- local image upload
- photo deletion

### Intelligent Search

- natural-language search over uploaded photos
- AI query rewrite / normalization
- text embedding search
- hybrid ranking with embedding similarity and caption token matches

### People

- face extraction on uploaded photos
- clustering of the same person across photos
- people list with preview portraits
- person rename flow
- person-specific photo view

## Tech Stack

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
- plain CSS

### AI Module

- OpenCLIP
- PyTorch
- Transformers
- InsightFace
- ONNX Runtime

## Repository Layout

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

## Local Development

### Frontend

Install dependencies:

```bash
cd WebUI && pnpm install
```

Run Vite dev server:

```bash
cd WebUI && pnpm dev
```

Run Vite on LAN:

```bash
cd WebUI && pnpm dev --host 0.0.0.0
```

Build production frontend bundle:

```bash
cd WebUI && pnpm build
```

### Backend

Install Python dependencies into your environment:

```bash
pip install -r Backend/requirements.txt
```

Run Django checks:

```bash
.venv/bin/python Backend/manage.py check
```

Run migrations:

```bash
.venv/bin/python Backend/manage.py migrate
```

Start the integrated app flow:

```bash
python Backend/run_app.py
```

That command:

- ensures `WebUI` dependencies exist
- builds the frontend bundle
- applies migrations
- runs `collectstatic`
- starts Django on `http://127.0.0.1:8000/`

You can also run Django directly:

```bash
.venv/bin/python Backend/manage.py runserver 127.0.0.1:8000
```

## Configuration

### Local Data

By default the app stores its SQLite database and uploaded files under `Local_DB/`.

```env
LIQUID_PHOTOS_DATA_DIR=./Local_DB
DJANGO_ALLOWED_HOSTS=*
DJANGO_DEBUG=true
```

Typical structure:

```text
Local_DB/
├── db.sqlite3
└── media/
    └── users/
        └── <username>/
            ├── <uuid>.jpg
            └── faces/
```

### AI Runtime

AI runtime behavior is controlled through `CoreAI.config`.

Important examples:

- `bEnableAiModule`
- `bEnableFaceModule`
- `sComputeDevice`
- `sQueryRewriteModelPath`

The Django app imports the AI module from `CoreAI/`, but the runtime itself lives inside the Python package `nova_ai_shipping`.

## Main Backend Endpoints

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

## Notes

- UI text should remain Russian by default
- registration is currently closed in backend logic
- `README` should be treated as current architecture guidance, not as a historical prototype note
