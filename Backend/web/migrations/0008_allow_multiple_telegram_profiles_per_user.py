from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("web", "0007_photo_entity_payload_photo_search_synonyms_ru_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="telegramprofile",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="telegram_profiles",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
