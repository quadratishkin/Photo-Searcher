#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/Backend"
WEB_UI_DIR="$SCRIPT_DIR/WebUI"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
HOST_AND_PORT="${1:-127.0.0.1:8000}"

if ! command -v pnpm >/dev/null 2>&1; then
  echo "Ошибка: pnpm не найден в PATH." >&2
  exit 1
fi

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Ошибка: не найден Python в .venv/bin/python." >&2
  exit 1
fi

if [[ ! -d "$WEB_UI_DIR/node_modules" ]]; then
  echo "Устанавливаем зависимости WebUI..."
  (cd "$WEB_UI_DIR" && pnpm install)
fi

echo "Собираем WebUI..."
(cd "$WEB_UI_DIR" && pnpm build)

echo "Применяем миграции..."
(cd "$BACKEND_DIR" && "$VENV_PYTHON" manage.py migrate --noinput)

echo "Собираем static..."
(cd "$BACKEND_DIR" && "$VENV_PYTHON" manage.py collectstatic --noinput)

echo "Запускаем Django на http://$HOST_AND_PORT/"
cd "$BACKEND_DIR"
exec "$VENV_PYTHON" manage.py runserver "$HOST_AND_PORT"
