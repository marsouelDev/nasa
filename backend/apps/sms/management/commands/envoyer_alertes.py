"""Commande Celery : envoi des alertes de risque aux consentants."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.sms.tasks import envoyer_alertes_risque


class Command(BaseCommand):
    help = "Évalue les risques et prépare les alertes SMS aux consentants (Celery eager)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--zone",
            type=str,
            default=None,
            help="Slug de zone. Par défaut : toutes les zones actives.",
        )

    def handle(self, *args, **options):
        resultat = envoyer_alertes_risque.delay(options.get("zone") or None)
        self.stdout.write(f"Alertes SMS : {resultat}")
        return resultat
