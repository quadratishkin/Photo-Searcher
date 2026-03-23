from django.apps import AppConfig


class WebConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "web"

    def ready(self) -> None:
        from nova_ai_shipping.runtime import load_ai_module

        load_ai_module()
