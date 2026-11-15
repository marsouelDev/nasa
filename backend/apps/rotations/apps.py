"""Configuration de l'application rotations."""

from django.apps import AppConfig


class RotationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.rotations"
    label = "rotations"
    verbose_name = "Rotations de cultures"
