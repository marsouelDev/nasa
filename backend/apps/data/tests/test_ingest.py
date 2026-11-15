"""Tests de la commande d'ingestion (HTTP simulé, base de test)."""

from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from apps.data.models import IngestionLog, Zone
from apps.data.services import power

from .aides import donnees_power, power_payload


class IngestPowerTests(TestCase):
    def setUp(self):
        self.zone = Zone.objects.create(
            nom="Ville test",
            slug="testville",
            latitude=4.75,
            longitude=11.23,
        )

    def lancer(self, **options):
        options.setdefault("no_csv", True)
        sortie = StringIO()
        call_command(
            "ingest_power",
            zone="testville",
            start="2016-01-01",
            end="2016-01-10",
            stdout=sortie,
            stderr=StringIO(),
            **options,
        )
        return sortie.getvalue()

    @patch("apps.data.management.commands.ingest_power.time.sleep")
    def test_ingestion_enregistre_les_jours_et_le_journal(self, _sleep):
        with patch(
            "apps.data.services.power.fetch_interval", return_value=donnees_power(
                date(2016, 1, 1), 10, pluie=3.5
            )
        ) as fetch:
            self.lancer()

        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(self.zone.weather.count(), 10)
        ligne = self.zone.weather.get(date=date(2016, 1, 5))
        self.assertEqual(ligne.precip_mm, 3.5)
        journal = IngestionLog.objects.filter(zone=self.zone).latest("cree_le")
        self.assertEqual(journal.statut, IngestionLog.Statut.SUCCES)
        self.assertEqual(journal.jours_recus, 10)

    @patch("apps.data.management.commands.ingest_power.time.sleep")
    def test_cache_evite_un_second_telechargement(self, _sleep):
        with patch(
            "apps.data.services.power.fetch_interval",
            return_value=donnees_power(date(2016, 1, 1), 10),
        ) as fetch:
            self.lancer()
            self.assertEqual(fetch.call_count, 1)
            fetch.reset_mock()
            sortie = self.lancer()

        self.assertEqual(fetch.call_count, 0)
        self.assertIn("Cache complet", sortie)
        self.assertEqual(self.zone.weather.count(), 10)

    @patch("apps.data.management.commands.ingest_power.time.sleep")
    def test_seules_les_dates_manquantes_sont_demandees(self, _sleep):
        with patch(
            "apps.data.services.power.fetch_interval",
            return_value=donnees_power(date(2016, 1, 1), 10),
        ):
            self.lancer()

        self.zone.weather.filter(date__range=(date(2016, 1, 5), date(2016, 1, 6))).delete()

        def fetch(zone, debut, fin, timeout=None):
            from apps.data.services import power

            return power.parse_payload(
                power_payload(debut, (fin - debut).days + 1, pluie=1.5)
            )

        with patch("apps.data.services.power.fetch_interval", side_effect=fetch) as simule:
            self.lancer()

        self.assertEqual(simule.call_count, 1)
        args = simule.call_args
        self.assertEqual(args.args[1], date(2016, 1, 5))
        self.assertEqual(args.args[2], date(2016, 1, 6))
        self.assertEqual(self.zone.weather.count(), 10)
        self.assertEqual(self.zone.weather.get(date=date(2016, 1, 6)).precip_mm, 1.5)

    @patch("apps.data.management.commands.ingest_power.time.sleep")
    def test_force_ecrase_les_valeurs_existantes(self, _sleep):
        with patch(
            "apps.data.services.power.fetch_interval",
            return_value=donnees_power(date(2016, 1, 1), 10, pluie=1.0),
        ):
            self.lancer()

        with patch(
            "apps.data.services.power.fetch_interval",
            return_value=donnees_power(date(2016, 1, 1), 10, pluie=9.0),
        ) as fetch:
            self.lancer(force=True)

        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(self.zone.weather.get(date=date(2016, 1, 5)).precip_mm, 9.0)

    @patch("apps.data.management.commands.ingest_power.time.sleep")
    def test_valeurs_entierement_manquantes_ignorees(self, _sleep):
        charge = power_payload(date(2016, 1, 1), 10)
        for parametre in charge["properties"]["parameter"].values():
            parametre["20160104"] = -999

        with patch(
            "apps.data.services.power.fetch_interval",
            return_value=power.parse_payload(charge),
        ):
            self.lancer()

        self.assertEqual(self.zone.weather.count(), 9)
        self.assertFalse(self.zone.weather.filter(date=date(2016, 1, 4)).exists())
        journal = IngestionLog.objects.filter(zone=self.zone).latest("cree_le")
        self.assertEqual(journal.jours_ignores, 1)

    @patch("apps.data.management.commands.ingest_power.time.sleep")
    def test_export_csv_en_utf8_avec_bom(self, _sleep):
        with TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "power.csv"
            with patch(
                "apps.data.services.power.fetch_interval",
                return_value=donnees_power(date(2016, 1, 1), 10, pluie=2.0),
            ):
                self.lancer(no_csv=False, csv_path=str(chemin))

            self.assertTrue(chemin.exists())
            contenu = chemin.read_bytes()
            self.assertTrue(contenu.startswith(b"\xef\xbb\xbf"))
            lignes = chemin.read_text(encoding="utf-8-sig").strip().splitlines()
            self.assertEqual(lignes[0], "date,precip_mm,tmax_c,tmin_c")
            self.assertEqual(len(lignes), 11)

    def test_zone_inconnue_donne_une_erreur_claire(self):
        from django.core.management.base import CommandError

        with self.assertRaisesMessage(CommandError, "Zone « absente » inconnue"):
            call_command(
                "ingest_power",
                zone="absente",
                start="2016-01-01",
                end="2016-01-10",
                no_csv=True,
                stdout=StringIO(),
                stderr=StringIO(),
            )

    def test_date_invalide(self):
        from django.core.management.base import CommandError

        with self.assertRaisesMessage(CommandError, "start invalide"):
            call_command(
                "ingest_power",
                zone="testville",
                start="01/01/2016",
                end="2016-01-10",
                no_csv=True,
                stdout=StringIO(),
                stderr=StringIO(),
            )
