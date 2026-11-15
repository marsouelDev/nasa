"""Configuration de l'application data."""

from django.apps import AppConfig


class DataConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.data"
    label = "data"
    verbose_name = "Données NASA et zones"
