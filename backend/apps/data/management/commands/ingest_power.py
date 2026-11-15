"""Ingestion des données journalières NASA POWER avec cache incrémental."""

from __future__ import annotations

import csv
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.data.models import DailyWeather, IngestionLog, Zone
from apps.data.services import power


def _date(valeur: str, nom: str) -> date:
    try:
        return datetime.strptime(valeur, "%Y-%m-%d").date()
    except ValueError as exc:
        raise CommandError(f"--{nom} invalide « {valeur} » : format attendu AAAA-MM-JJ.") from exc


class Command(BaseCommand):
    help = (
        "Télécharge les données NASA POWER journalières pour une zone, "
        "en ne récupérant que les dates absentes de la base (cache incrémental)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--zone", default=settings.DEFAULT_ZONE_SLUG, help="Identifiant (slug) de la zone."
        )
        parser.add_argument("--start", default="2016-01-01", help="Première date (AAAA-MM-JJ).")
        parser.add_argument(
            "--end",
            default="auto",
            help="Dernière date (AAAA-MM-JJ) ou « auto » = aujourd'hui - 2 jours.",
        )
        parser.add_argument(
            "--force", action="store_true", help="Retélécharge et écrase les données existantes."
        )
        parser.add_argument("--csv", dest="csv_path", default=None, help="Chemin du CSV exporté.")
        parser.add_argument("--no-csv", action="store_true", help="N'exporte pas de CSV.")
        parser.add_argument("--timeout", type=int, default=None, help="Timeout HTTP en secondes.")

    def handle(self, *args, **options):
        zone = Zone.objects.filter(slug=options["zone"]).first()
        if zone is None:
            raise CommandError(
                f"Zone « {options['zone']} » inconnue. Créez-la avec : "
                f"python manage.py creer_zone --slug {options['zone']} --nom \"...\" --lat ... --lon ..."
            )

        debut = _date(options["start"], "start")
        fin = (
            date.today() - timedelta(days=2)
            if options["end"] == "auto"
            else _date(options["end"], "end")
        )
        if debut > fin:
            raise CommandError("--start doit précéder --end.")

        journal = IngestionLog.objects.create(
            zone=zone,
            debut=debut,
            fin=fin,
            statut=IngestionLog.Statut.PARTIEL,
            message="Ingestion démarrée.",
        )

        existantes = set(
            zone.weather.filter(date__range=(debut, fin)).values_list("date", flat=True)
        )
        periodes = (
            [(debut, fin)]
            if options["force"]
            else power.periodes_manquantes(debut, fin, existantes)
        )

        self.stdout.write(
            f"Zone {zone.nom} ({zone.latitude:.2f}, {zone.longitude:.2f}) — "
            f"{debut} → {fin} ; {len(existantes)} jour(s) déjà en base."
        )

        if not periodes:
            self.stdout.write(self.style.SUCCESS("Cache complet : aucun téléchargement nécessaire."))
            journal.statut = IngestionLog.Statut.SUCCES
            journal.message = "Cache complet."
            journal.termine_le = timezone.now()
            journal.save(update_fields=["statut", "message", "termine_le"])
        else:
            recus, ignores, erreurs = self._ingerer(
                zone, debut, fin, periodes, options["timeout"], options["force"]
            )
            journal.jours_recus = recus
            journal.jours_ignores = ignores
            journal.termine_le = timezone.now()
            if erreurs and recus == 0:
                journal.statut = IngestionLog.Statut.ERREUR
                journal.message = " | ".join(erreurs)
            elif erreurs:
                journal.statut = IngestionLog.Statut.PARTIEL
                journal.message = " | ".join(erreurs)
            else:
                journal.statut = IngestionLog.Statut.SUCCES
                journal.message = f"{recus} jour(s) enregistré(s), {ignores} ignoré(s)."
            journal.save(
                update_fields=[
                    "jours_recus",
                    "jours_ignores",
                    "statut",
                    "message",
                    "termine_le",
                ]
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Ingestion terminée : {recus} jour(s) enregistré(s), "
                    f"{ignores} valeur(s) entièrement manquante(s) ignorée(s)."
                )
            )
            if erreurs:
                for erreur in erreurs:
                    self.stderr.write(self.style.WARNING(f"Erreur : {erreur}"))

        if not options["no_csv"]:
            chemin = self._exporter_csv(zone, options["csv_path"])
            self.stdout.write(f"CSV exporté (UTF-8) : {chemin}")

        total = zone.weather.count()
        self.stdout.write(f"Total en base pour {zone.slug} : {total} jour(s).")

    def _ingerer(self, zone, debut, fin, periodes, timeout, force):
        recus = 0
        ignores = 0
        erreurs: list[str] = []

        for periode_debut, periode_fin in periodes:
            for lot_debut, lot_fin in power.decouper_periode(periode_debut, periode_fin):
                self.stdout.write(f"  Téléchargement {lot_debut} → {lot_fin}…")
                try:
                    donnees = power.fetch_interval(zone, lot_debut, lot_fin, timeout=timeout)
                except (power.PowerError, ValueError) as exc:
                    erreurs.append(f"{lot_debut}→{lot_fin} : {exc}")
                    continue

                a_enregistrer: list[DailyWeather] = []
                for jour, valeurs in sorted(donnees.items()):
                    if jour < debut or jour > fin:
                        continue
                    if all(valeur is None for valeur in valeurs.values()):
                        ignores += 1
                        continue
                    a_enregistrer.append(
                        DailyWeather(zone=zone, date=jour, source="NASA POWER", **valeurs)
                    )

                if a_enregistrer:
                    if force:
                        DailyWeather.objects.bulk_create(
                            a_enregistrer,
                            update_conflicts=True,
                            unique_fields=["zone", "date"],
                            update_fields=["precip_mm", "tmax_c", "tmin_c", "source", "ingere_le"],
                        )
                    else:
                        DailyWeather.objects.bulk_create(a_enregistrer, ignore_conflicts=True)
                    recus += len(a_enregistrer)

                # Petite pause pour rester courtois avec l'API publique.
                time.sleep(0.3)

        return recus, ignores, erreurs

    def _exporter_csv(self, zone: Zone, chemin: str | None) -> Path:
        destination = (
            Path(chemin)
            if chemin
            else settings.BASE_DIR / "exports" / f"power_{zone.slug}.csv"
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", newline="", encoding="utf-8-sig") as fichier:
            writer = csv.writer(fichier)
            writer.writerow(["date", "precip_mm", "tmax_c", "tmin_c"])
            for jour, pluie, tmax, tmin in zone.weather.order_by("date").values_list(
                "date", "precip_mm", "tmax_c", "tmin_c"
            ):
                writer.writerow(
                    [
                        jour.isoformat(),
                        "" if pluie is None else pluie,
                        "" if tmax is None else tmax,
                        "" if tmin is None else tmin,
                    ]
                )
        return destination
