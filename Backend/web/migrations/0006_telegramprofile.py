from django.db import migrations, models
from django.conf import settings
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("web", "0005_photo_ru_captions"),
    ]

    operations = [
        migrations.CreateModel(
            name="TelegramProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("telegram_user_id", models.BigIntegerField(unique=True)),
                ("telegram_chat_id", models.BigIntegerField(unique=True)),
                ("telegram_username", models.CharField(blank=True, max_length=255)),
                ("telegram_first_name", models.CharField(blank=True, max_length=255)),
                ("telegram_last_name", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="telegram_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["id"]},
        ),
    ]
