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
