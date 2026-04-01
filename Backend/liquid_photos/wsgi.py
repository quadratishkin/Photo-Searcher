import os

from django.core.wsgi import get_wsgi_application

from liquid_photos.env import load_project_env

load_project_env()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "liquid_photos.settings")

application = get_wsgi_application()
