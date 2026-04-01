#!/usr/bin/env python
import os
import sys

from liquid_photos.env import load_project_env


def main() -> None:
    load_project_env()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "liquid_photos.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
