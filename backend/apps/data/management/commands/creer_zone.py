"""Crée ou met à jour une zone suivie (les coordonnées vivent en base)."""

from django.core.management.base import BaseCommand, CommandError

from apps.data.models import Zone


class Command(BaseCommand):
    help = "Crée ou met à jour une zone (slug, nom, latitude, longitude)."

    def add_arguments(self, parser):
        parser.add_argument("--slug", required=True)
        parser.add_argument("--nom", required=True)
        parser.add_argument("--lat", type=float, required=True)
        parser.add_argument("--lon", type=float, required=True)
        parser.add_argument("--altitude", type=float, default=None)
        parser.add_argument("--pays", default="Cameroun")

    def handle(self, *args, **options):
        if not -90 <= options["lat"] <= 90:
            raise CommandError("Latitude attendue entre -90 et 90.")
        if not -180 <= options["lon"] <= 180:
            raise CommandError("Longitude attendue entre -180 et 180.")

        zone, creee = Zone.objects.update_or_create(
            slug=options["slug"],
            defaults={
                "nom": options["nom"],
                "pays": options["pays"],
                "latitude": options["lat"],
                "longitude": options["lon"],
                "altitude_m": options["altitude"],
                "actif": True,
            },
        )
        action = "créée" if creee else "mise à jour"
        self.stdout.write(self.style.SUCCESS(f"Zone {zone.slug} {action} : {zone}"))
