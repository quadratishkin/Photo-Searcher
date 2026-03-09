FROM node:22-bookworm-slim AS frontend-build

WORKDIR /app

COPY package.json pnpm-lock.yaml tsconfig.json tsconfig.app.json vite.config.ts index.html ./
COPY src ./src
COPY public ./public

RUN corepack enable \
    && pnpm install --frozen-lockfile \
    && pnpm build

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY manage.py run_app.py CoreAI.config ./
COPY liquid_photos ./liquid_photos
COPY photo_ai ./photo_ai
COPY web ./web
COPY templates ./templates
COPY public ./public
COPY --from=frontend-build /app/frontend_build ./frontend_build

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
