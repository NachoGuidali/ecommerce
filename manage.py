#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # Este error indica que Django no está instalado o falta el entorno
        raise ImportError(
            "Couldn't import Django. Asegúrate de tenerlo instalado "
            "y de activar tu virtualenv."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
