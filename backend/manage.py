#!/usr/bin/env python
"""Utilitaire de ligne de commande Django pour AgroSentry."""
import os
import sys

from dotenv import load_dotenv


def main():
    # Console Windows : évite les UnicodeEncodeError sur les accents et flèches.
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # flux redirigé sans reconfigure
            pass
    # Charge le .env de la racine du dépôt (backend/..).
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "agrosentry.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django est introuvable. Activez le venv puis installez requirements.txt."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
