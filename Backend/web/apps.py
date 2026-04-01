import os
import sys

from django.apps import AppConfig


class WebConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "web"

    def ready(self) -> None:
        if len(sys.argv) > 1 and sys.argv[1] not in {"runserver", "run_telegram_bot"}:
            return

        from CoreAI.runtime import load_ai_module

        load_ai_module()

        if sys.argv[1] != "runserver":
            return
        if os.environ.get("LIQUID_PHOTOS_RUN_TELEGRAM_INSIDE_SERVER", "").strip().lower() not in {"1", "true", "yes", "on"}:
            return

        from web.telegram_bot import start_polling_background

        start_polling_background()
