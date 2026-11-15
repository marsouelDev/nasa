"""Entraîne le modèle de risque de poche de sécheresse (Random Forest)."""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.data.models import Zone
from apps.ml import services


class Command(BaseCommand):
    help = (
        "Entraîne le Random Forest du risque de poche de sécheresse à partir des "
        "données NASA POWER en base, puis sauvegarde le modèle (joblib)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--zone", default=settings.DEFAULT_ZONE_SLUG, help="Identifiant (slug) de la zone."
        )
        parser.add_argument("--output", default=None, help="Chemin du fichier joblib de sortie.")

    def handle(self, *args, **options):
        zone = Zone.objects.filter(slug=options["zone"], actif=True).first()
        if zone is None:
            raise CommandError(
                f"Zone « {options['zone']} » inconnue. Créez-la avec : "
                f"python manage.py creer_zone --slug ... --nom ... --lat ... --lon ..."
            )

        lignes = list(
            zone.weather.order_by("date").values_list("date", "precip_mm", "tmax_c", "tmin_c")
        )
        if not lignes:
            raise CommandError(
                f"Aucune donnée météo en base pour la zone « {zone.slug} ». "
                f"Lancez d'abord : python manage.py ingest_power --zone {zone.slug}"
            )

        dataframe = services.construire_dataframe(lignes)
        jeu = dataframe.dropna(subset=(*services.COLONNES, "target"))
        self.stdout.write(
            f"Zone {zone.slug} : {len(lignes)} jour(s) en série, {len(jeu)} exemple(s) exploitables."
        )

        artefact = services.entrainer(dataframe)
        chemin = services.sauvegarder(
            artefact,
            Path(options["output"]) if options["output"] else services.CHEMIN_MODELE,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Modèle entraîné : précision de validation temporelle "
                f"(TimeSeriesSplit, gap={15}) = {artefact['precision_cv_balanced_accuracy']:.2f}"
            )
        )
        self.stdout.write(f"Variables importantes : {artefact['variables_importantes']}")
        self.stdout.write(f"Modèle sauvegardé : {chemin}")
