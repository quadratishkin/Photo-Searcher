from __future__ import annotations

from django.core.management.base import BaseCommand

from web.telegram_bot import run_polling


class Command(BaseCommand):
    help = "Запускает Telegram-бота Liquid Photos."

    def handle(self, *args, **options):
        run_polling()
