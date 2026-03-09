#!/bin/sh
set -eu

cd /app

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ -n "${APP_DEFAULT_USERNAME:-}" ] && [ -n "${APP_DEFAULT_PASSWORD:-}" ]; then
  python manage.py shell <<'PY'
import os

from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ["APP_DEFAULT_USERNAME"]
password = os.environ["APP_DEFAULT_PASSWORD"]
is_staff = os.environ.get("APP_DEFAULT_IS_STAFF", "false").strip().lower() in {"1", "true", "yes", "on"}
is_superuser = os.environ.get("APP_DEFAULT_IS_SUPERUSER", "false").strip().lower() in {"1", "true", "yes", "on"}

user, created = User.objects.get_or_create(
    username=username,
    defaults={"is_staff": is_staff, "is_superuser": is_superuser},
)

changed = False
if created:
    changed = True

if user.is_staff != is_staff:
    user.is_staff = is_staff
    changed = True

if user.is_superuser != is_superuser:
    user.is_superuser = is_superuser
    changed = True

if not user.check_password(password):
    user.set_password(password)
    changed = True

if changed:
    user.save()
PY
fi

exec python manage.py runserver 0.0.0.0:${PORT:-8000}
