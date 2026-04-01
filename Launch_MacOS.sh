#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/Backend"
WEB_UI_DIR="$SCRIPT_DIR/WebUI"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
ENV_FILE="$SCRIPT_DIR/.env.local"
BIND_ADDRESS="${1:-0.0.0.0:8000}"
BIND_HOST="${BIND_ADDRESS%%:*}"
BIND_PORT="${BIND_ADDRESS##*:}"
LOCAL_APP_URL="http://127.0.0.1:$BIND_PORT/"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

stop_matching_processes() {
  local label="$1"
  shift
  local pids=()
  local pattern
  for pattern in "$@"; do
    while IFS= read -r pid; do
      [[ -n "$pid" ]] || continue
      [[ "$pid" == "$$" ]] && continue
      pids+=("$pid")
    done < <(pgrep -f "$pattern" || true)
  done

  if [[ "${#pids[@]}" -eq 0 ]]; then
    return
  fi

  local unique_pids=()
  local pid
  for pid in "${pids[@]}"; do
    if [[ " ${unique_pids[*]} " == *" $pid "* ]]; then
      continue
    fi
    unique_pids+=("$pid")
  done

  echo "Останавливаем предыдущие процессы $label: ${unique_pids[*]}"
  kill "${unique_pids[@]}" >/dev/null 2>&1 || true
  sleep 1
  for pid in "${unique_pids[@]}"; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
  done
}

stop_project_runservers() {
  local pids=()
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    [[ "$pid" == "$$" ]] && continue
    pids+=("$pid")
  done < <(pgrep -f "$SCRIPT_DIR/.venv/bin/python .*manage.py runserver .*--noreload" || true)

  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    [[ "$pid" == "$$" ]] && continue
    pids+=("$pid")
  done < <(pgrep -f "Backend/manage.py runserver .*--noreload" || true)

  if [[ "${#pids[@]}" -eq 0 ]]; then
    return
  fi

  local unique_pids=()
  local pid
  for pid in "${pids[@]}"; do
    if [[ " ${unique_pids[*]} " == *" $pid "* ]]; then
      continue
    fi
    unique_pids+=("$pid")
  done

  echo "Останавливаем предыдущие Django-процессы проекта: ${unique_pids[*]}"
  kill "${unique_pids[@]}" >/dev/null 2>&1 || true
  sleep 1
  for pid in "${unique_pids[@]}"; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
  done
}

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

stop_matching_processes "Telegram-бота" \
  "$SCRIPT_DIR/.venv/bin/python .*manage.py run_telegram_bot" \
  "Backend/manage.py run_telegram_bot"

stop_project_runservers

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}

cd "$BACKEND_DIR"
if [[ -n "${LIQUID_PHOTOS_TELEGRAM_BOT_TOKEN:-}" ]]; then
  export LIQUID_PHOTOS_RUN_TELEGRAM_INSIDE_SERVER=1
  echo "Telegram-бот будет поднят внутри процесса Django."
else
  export LIQUID_PHOTOS_RUN_TELEGRAM_INSIDE_SERVER=0
  echo "Telegram-бот пропущен: не найден LIQUID_PHOTOS_TELEGRAM_BOT_TOKEN в $ENV_FILE." >&2
fi

echo "Запускаем Django на http://$BIND_ADDRESS/"
"$VENV_PYTHON" manage.py runserver "$BIND_ADDRESS" --noreload &
SERVER_PID=$!

trap cleanup EXIT INT TERM

echo "Ждём готовности сервера..."
for _ in {1..60}; do
  if curl -fsS "$LOCAL_APP_URL" >/dev/null 2>&1; then
    echo "Открываем браузер: $LOCAL_APP_URL"
    open "$LOCAL_APP_URL"
    if [[ "$BIND_HOST" == "0.0.0.0" ]]; then
      LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
      if [[ -n "$LAN_IP" ]]; then
        echo "Из локальной сети приложение доступно по адресу: http://$LAN_IP:$BIND_PORT/"
      fi
    fi
    wait "$SERVER_PID"
    exit $?
  fi

  if ! kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    wait "$SERVER_PID"
    exit $?
  fi

  sleep 1
done

echo "Ошибка: сервер не стал доступен по адресу $LOCAL_APP_URL за 60 секунд." >&2
exit 1
